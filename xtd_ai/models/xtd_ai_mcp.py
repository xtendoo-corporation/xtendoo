import base64
import json
import logging
import time

from odoo import api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError

from ..tools.errors import XtdAiDraftOnlyError, XtdAiRpcError, XtdAiToolError
from ..tools.schema import validate

_logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
MAX_RESULT_BYTES = 200_000
MAX_REPLY_TEXT = 50_000
DEFAULT_MAX_TOOL_CALLS = 30


class XtdAiMcp(models.AbstractModel):
    """JSON-RPC 2.0 / MCP message handler (CONTRACT §4).

    ``_xtd_ai_handle`` expects an environment built by the ``xtd_ai`` auth
    method: session user, ``su=False``, ``allowed_company_ids`` and
    ``xtd_ai_run`` in the context.
    """

    _name = "xtd.ai.mcp"
    _description = "AI agent MCP handler"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_handle(self, message):
        """Handle one JSON-RPC message. Returns ``(http_status, response_dict)``."""
        request_id = message.get("id") if isinstance(message, dict) else None
        try:
            if (
                not isinstance(message, dict)
                or message.get("jsonrpc") != "2.0"
                or not isinstance(message.get("method"), str)
                or "id" not in message
                or isinstance(request_id, bool)
                or (request_id is not None and not isinstance(request_id, (str, int)))
            ):
                raise XtdAiRpcError(200, -32600, "Invalid Request")
            params = message.get("params")
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise XtdAiRpcError(200, -32602, "Invalid params")
            run = self._xtd_ai_current_run()
            run._xtd_ai_touch_running()
            method = message["method"]
            handler = {
                "initialize": self._xtd_ai_m_initialize,
                "tools/list": self._xtd_ai_m_tools_list,
                "tools/call": self._xtd_ai_m_tools_call,
                "xtd_ai/history": self._xtd_ai_m_history,
                "xtd_ai/post_reply": self._xtd_ai_m_post_reply,
                "xtd_ai/attachment": self._xtd_ai_m_attachment,
            }.get(method)
            if handler is None:
                raise XtdAiRpcError(200, -32601, "Method not found")
            result = handler(run, params)
            return 200, {"jsonrpc": "2.0", "id": request_id, "result": result}
        except XtdAiRpcError as exc:
            return exc.http_status, {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": exc.rpc_code, "message": exc.message},
            }

    @api.model
    def _xtd_ai_dispatch(self, method, params=None):
        """In-process call of one MCP method (CONTRACT section 15).

        Runs exactly what ``POST /xtd_ai/mcp`` runs, with the same audit and
        guards, using an environment built by
        ``xtd.ai.run._xtd_ai_runner_env``.

        :returns: the JSON-RPC ``result``.
        :raises: ``XtdAiRpcError`` for protocol-level errors.
        """
        status, response = self._xtd_ai_handle(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        )
        error = response.get("error")
        if error:
            raise XtdAiRpcError(status, error["code"], error["message"])
        return response["result"]

    @api.model
    def _xtd_ai_current_run(self):
        run_id = self.env.context.get("xtd_ai_run")
        if not run_id:
            raise XtdAiRpcError(401, -32001, "Invalid credentials")
        # sudo: control record of the gateway; the auth method already verified it.
        return self.env["xtd.ai.run"].sudo().browse(run_id)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def _xtd_ai_m_initialize(self, run, params):
        if "protocolVersion" in params and not isinstance(
            params["protocolVersion"], str
        ):
            raise XtdAiRpcError(200, -32602, "Invalid params")
        version = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "xtd_ai")], limit=1)
            .installed_version
            or "19.0.1.0.0"
        )
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": "xtd_ai", "version": version},
            "capabilities": {"tools": {}},
        }

    def _xtd_ai_m_tools_list(self, run, params):
        toolbox = self.env["xtd.ai.toolbox"]
        return {
            "tools": [
                toolbox._xtd_ai_tool_descriptor(tool)
                for tool in toolbox._xtd_ai_visible_tools().values()
            ]
        }

    def _xtd_ai_m_history(self, run, params):
        user = self.env.user
        company = self.env.company
        conversation = run.conversation_id
        return {
            "user": {
                "name": user.name,
                "lang": self.env.context.get("lang") or user.lang,
                "tz": self.env.context.get("tz") or user.tz,
            },
            "company": {
                "id": company.id,
                "name": company.name,
                "currency": company.currency_id.name,
            },
            "allowed_companies": [
                {"id": c.id, "name": c.name}
                for c in self.env["res.company"].browse(
                    self.env.context.get("allowed_company_ids") or []
                )
            ],
            "today": str(fields.Date.context_today(self)),
            "confirm_writes": user._xtd_ai_needs_confirmation("draft")
            or conversation._xtd_ai_run_has_attachments(),
            "messages": conversation._xtd_ai_history_messages(20),
        }

    def _xtd_ai_m_post_reply(self, run, params):
        text = params.get("text", "")
        status = params.get("status")
        error = params.get("error")
        usage = params.get("usage", {})
        if (
            not isinstance(text, str)
            or status not in ("done", "failed")
            or (error is not None and not isinstance(error, str))
            or not isinstance(usage, dict)
        ):
            raise XtdAiRpcError(200, -32602, "Invalid params")
        text = text[:MAX_REPLY_TEXT]
        messages = self.env[
            "xtd.ai.message"
        ].sudo()  # sudo: the gateway writes the reply
        body = text or (error or "")
        message = messages.create(
            {
                "conversation_id": run.conversation_id.id,
                "role": "assistant" if (status == "done" or text) else "notice",
                "body": body,
                "run_id": run.id,
                "record_refs": run.record_refs or False,
            }
        )
        self.env["xtd.ai.pending_action"].sudo().search(
            [("run_id", "=", run.id), ("message_id", "=", False)]
        ).write({"message_id": message.id})
        run._xtd_ai_finish(
            status, error=error if status == "failed" else None, usage=usage
        )
        run._xtd_ai_notify(message)
        return {"message_id": message.id}

    def _xtd_ai_m_attachment(self, run, params):
        """``xtd_ai/attachment``: content of a chat attachment (CONTRACT §14)."""
        att_id = params.get("id")
        if isinstance(att_id, bool) or not isinstance(att_id, int):
            raise XtdAiRpcError(200, -32602, "Invalid params")
        started = time.monotonic()

        def finish_audit(outcome, code=None):
            self.env["xtd.ai.audit"]._xtd_ai_log(
                "attachment_read",
                outcome,
                run_id=run.id,
                user_id=self.env.uid,
                company_id=self.env.company.id,
                error_code=code,
                arguments={"id": att_id},
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        # sudo: gateway-owned link table; it only tells whether the attachment
        # belongs to a message of the token's conversation. The content is then
        # read with the user's environment below.
        linked = (
            self.env["xtd.ai.message"]
            .sudo()
            .search_count(
                [
                    ("conversation_id", "=", run.conversation_id.id),
                    ("attachment_ids", "in", [att_id]),
                ]
            )
        )
        attachment = self.env["ir.attachment"].browse(att_id)
        try:
            if not linked or not attachment.exists():
                raise AccessError(self.env._("not linked"))
            attachment.check_access("read")
            name, mimetype, raw = attachment.name, attachment.mimetype, attachment.raw
        except (AccessError, MissingError):
            finish_audit("denied", "attachment_denied")
            raise XtdAiRpcError(403, -32003, "Attachment not accessible") from None
        max_bytes = self.env["xtd.ai.conversation"]._xtd_ai_attachment_limits()[0]
        if len(raw or b"") > max_bytes:
            finish_audit("error", "attachment_too_large")
            raise XtdAiRpcError(200, -32602, "Attachment too large")
        finish_audit("ok")
        return {
            "id": att_id,
            "name": name,
            "mimetype": mimetype,
            "data_base64": base64.b64encode(raw or b"").decode(),
        }

    # ------------------------------------------------------------------
    # tools/call
    # ------------------------------------------------------------------
    def _xtd_ai_m_tools_call(self, run, params):
        name = params.get("name")
        arguments = params.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise XtdAiRpcError(200, -32602, "Invalid params")
        started = time.monotonic()
        audit = {
            "run_id": run.id,
            "user_id": self.env.uid,
            "company_id": self.env.company.id,
            "tool_name": name[:100],
            "arguments": arguments,
        }

        def finish_audit(event, outcome, code=None, refs=None):
            audit.update(
                duration_ms=int((time.monotonic() - started) * 1000),
                error_code=code,
                record_refs=refs,
            )
            self.env["xtd.ai.audit"]._xtd_ai_log(event, outcome, **audit)

        limit = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtd_ai.max_tool_calls_per_run", DEFAULT_MAX_TOOL_CALLS)
            or DEFAULT_MAX_TOOL_CALLS
        )
        if run._xtd_ai_count_tool_call() > limit:
            finish_audit("tool_call", "denied", "tool_call_limit")
            raise XtdAiRpcError(409, -32004, "Tool call limit exceeded")

        toolbox = self.env["xtd.ai.toolbox"]
        tool = toolbox._xtd_ai_visible_tools().get(name)
        if tool is None:
            finish_audit("tool_call", "denied", "unknown_tool")
            raise XtdAiRpcError(200, -32601, "Tool not found")

        event, outcome, code, refs = "tool_call", "ok", None, None
        try:
            errors = validate(toolbox._xtd_ai_schema(tool), arguments)
            if errors:
                raise XtdAiToolError(
                    "validation",
                    self.env._("Argumentos no válidos: %s", "; ".join(errors[:5])),
                )
            # CONTRACT §14: a document is untrusted input, so when the message
            # that started the run carries attachments every write is confirmed.
            if tool["kind"] != "read" and (
                self.env.user._xtd_ai_needs_confirmation(tool["kind"])
                or run.conversation_id._xtd_ai_run_has_attachments()
            ):
                structured = self._xtd_ai_propose(run, tool, arguments)
                outcome = "pending"
            else:
                result = toolbox._xtd_ai_execute(tool, arguments)
                refs = result["records"]
                if refs:
                    run._xtd_ai_add_record_refs(
                        [ref | {"created": tool["kind"] != "read"} for ref in refs]
                    )
                structured = {"status": "ok", "data": result["data"], "records": refs}
            payload = json.dumps(structured, ensure_ascii=False, default=str)
            if len(payload.encode()) > MAX_RESULT_BYTES:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "El resultado es demasiado grande; usa filtros más concretos."
                    ),
                )
        except Exception as exc:
            structured, event, outcome, code = self._xtd_ai_error_result(exc)
            payload = json.dumps(structured, ensure_ascii=False, default=str)
        finish_audit(event, outcome, code, refs)
        return {
            "content": [{"type": "text", "text": payload}],
            "structuredContent": structured,
            "isError": structured.get("status") == "error",
        }

    def _xtd_ai_propose(self, run, tool, arguments):
        """Store a pending action and return the ``pending_confirmation`` result."""
        toolbox = self.env["xtd.ai.toolbox"]
        preview = toolbox._xtd_ai_preview(tool, arguments)
        # sudo: users cannot create pending actions through the ORM (read-only ACL).
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .create(
                {
                    "run_id": run.id,
                    "conversation_id": run.conversation_id.id,
                    "user_id": self.env.uid,
                    "tool_name": tool["name"],
                    "arguments": arguments,
                    "preview": preview,
                    "cids": list(
                        self.env.context.get("allowed_company_ids")
                        or [self.env.company.id]
                    ),
                }
            )
        )
        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "summary": preview["summary"][:500],
        }

    @api.model
    def _xtd_ai_error_result(self, exc):
        """Map an exception to ``(structuredContent, audit_event, outcome, code)``."""
        data = None
        event, outcome = "tool_call", "error"
        if isinstance(exc, XtdAiDraftOnlyError):
            code, message = "draft_only", str(exc)
            event, outcome = "guard_blocked", "denied"
        elif isinstance(exc, XtdAiToolError):
            code, message, data = exc.code, exc.message, exc.data
            if code == "ambiguous":
                outcome = "error"
        elif isinstance(exc, AccessError):
            code, message, outcome = "access_denied", str(exc), "denied"
        elif isinstance(exc, MissingError):
            code, message = "not_found", str(exc)
        elif isinstance(exc, UserError):
            code, message = "validation", str(exc)
        else:
            _logger.exception("Unexpected error in an AI tool")
            code, message = (
                "internal",
                self.env._("Error interno al ejecutar la herramienta."),
            )
        structured = {
            "status": "error",
            "error": {"code": code, "message": message[:500]},
        }
        if data:
            structured["data"] = data
        return structured, event, outcome, code

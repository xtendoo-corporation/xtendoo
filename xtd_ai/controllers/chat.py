import logging
import os
import re
from contextlib import suppress

import requests

from odoo import SUPERUSER_ID, _, api, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)

SERVICE_TIMEOUT = 5  # seconds, CONTRACT §10
MODEL_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
MESSAGES_LIMIT = 200
UPLOAD_MAX_BYTES = 10 * 1024 * 1024  # CONTRACT §14
UPLOAD_MAX_PER_MESSAGE = 5
UPLOAD_TYPES = {
    "application/pdf": (".pdf",),
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/webp": (".webp",),
}

# Suggestion chips: (tool that must be visible to the user, text, send_now, attach).
# Chips are only built from tools the user can actually use; the text is Spanish.
SUGGESTIONS = [
    ("search_sale_orders", "¿Qué presupuestos tengo en borrador?", True, False),
    ("search_invoices", "¿Qué facturas de clientes están vencidas?", True, False),
    ("get_stock_levels", "¿Qué stock hay del producto ", False, False),
    (
        "create_vendor_bill",
        "Crea una factura de proveedor a partir de un PDF",
        False,
        True,
    ),
    ("search_opportunities", "¿Cómo va mi pipeline de oportunidades?", True, False),
    (
        "search_purchase_orders",
        "¿Qué pedidos de compra están pendientes de recibir?",
        True,
        False,
    ),
    ("search_pickings", "¿Qué albaranes tengo pendientes de procesar?", True, False),
]
MAX_SUGGESTIONS = 4


def _sniff_mimetype(data):
    """Real type from the first bytes (never trust the browser's declared type)."""
    if data[:5] == b"%PDF-":
        return "application/pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _call_service(dbname, url, key, body, messages):
    """Post-commit: hand the committed run to the AI service.

    Runs after the request transaction was committed (so the service can call
    back into Odoo at once). Never logs the token nor the response body.
    ``messages`` holds the already translated failure notices.
    """
    error = None
    try:
        response = requests.post(
            f"{url.rstrip('/')}/v1/runs",
            json=body,
            headers={"X-XTD-AI-Service-Key": key},
            timeout=SERVICE_TIMEOUT,
        )
        if response.status_code != 202:
            _logger.warning(
                "AI service rejected run %s: HTTP %s",
                body["run_id"],
                response.status_code,
            )
            error = messages["rejected"] % response.status_code
    except Exception as exc:  # noqa: BLE001 - any failure must fail the run
        _logger.warning(
            "AI service call failed for run %s: %s", body["run_id"], type(exc).__name__
        )
        error = messages["unreachable"]
    if error:
        try:
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["xtd.ai.run"].browse(body["run_id"])._xtd_ai_fail(error)
        except Exception:
            _logger.exception("Could not mark run %s as failed", body["run_id"])


class XtdAiChatController(http.Controller):
    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _env(self):
        env = request.env
        env["xtd.ai.conversation"]._xtd_ai_check_user(env.user)
        return env

    def _conversation(self, env, conversation_id):
        conversation = env["xtd.ai.conversation"].search(
            [("id", "=", int(conversation_id or 0)), ("user_id", "=", env.uid)]
        )
        if not conversation:
            raise AccessError(_("Esta conversación no es tuya."))
        return conversation

    def _record_link(self, model, res_id):
        if not isinstance(model, str) or not MODEL_RE.match(model):
            return None
        if not isinstance(res_id, int) or isinstance(res_id, bool) or res_id <= 0:
            return None
        return f"/odoo/{model}/{res_id}"

    def _refs(self, refs):
        result = []
        for ref in refs or []:
            if not isinstance(ref, dict):
                continue
            url = self._record_link(ref.get("model"), ref.get("id"))
            if url:
                result.append(
                    {
                        "model": ref["model"],
                        "id": ref["id"],
                        "name": str(ref.get("name") or ref["model"])[:100],
                        "created": bool(ref.get("created")),
                        "url": url,
                    }
                )
        return result

    @staticmethod
    def _preview_text(value):
        """Plain text of a preview value (tools wrap free text and money)."""
        if isinstance(value, dict):
            if "untrusted_text" in value:
                return str(value["untrusted_text"] or "")
            if "amount" in value:
                return f"{value['amount']:,.2f} {value.get('currency') or ''}".strip()
            if "name" in value:
                return str(value["name"] or "")
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(
                filter(None, (XtdAiChatController._preview_text(v) for v in value))
            )
        if value is None or value is False:
            return ""
        return str(value)

    @classmethod
    def _preview_line(cls, line):
        """One preview line as ``{field, value}`` whatever the tool's structure.

        Generic ``{field, value}`` lines pass through; document lines (product,
        quantity, price, subtotal, taxes...) become one readable line.
        """
        if "field" in line or "value" in line:
            return {
                "field": str(line.get("field", ""))[:60],
                "value": cls._preview_text(line.get("value"))[:300],
            }
        label = cls._preview_text(line.get("product")) or cls._preview_text(
            line.get("description") or line.get("name")
        )
        parts = []
        if line.get("quantity") not in (None, False):
            qty = line["quantity"]
            parts.append(f"{qty:g}" if isinstance(qty, float) else str(qty))
        price = cls._preview_text(line.get("price_unit"))
        if price:
            parts.append(f"× {price}")
        if line.get("discount"):
            parts.append(f"(-{line['discount']:g} %)")
        subtotal = cls._preview_text(line.get("subtotal"))
        if subtotal:
            parts.append(f"= {subtotal}")
        taxes = cls._preview_text(line.get("taxes"))
        if taxes:
            parts.append(f"[{taxes}]")
        if not parts:
            parts = [
                f"{key}: {cls._preview_text(value)}"
                for key, value in line.items()
                if key not in ("product", "description", "name")
                and cls._preview_text(value)
            ]
        return {"field": label[:60], "value": " ".join(parts)[:300]}

    def _action_payload(self, env, action):
        closed = action.conversation_id.state != "open"
        tool = env["xtd.ai.toolbox"]._xtd_ai_tools().get(action.tool_name)
        preview = action.preview if isinstance(action.preview, dict) else {}
        lines = [
            self._preview_line(line)
            for line in preview.get("lines") or []
            if isinstance(line, dict)
        ]
        result = None
        if action.state == "confirmed" and action.result_model and action.result_res_id:
            url = self._record_link(action.result_model, action.result_res_id)
            name = action.result_model
            # no access or gone: keep a generic label
            with suppress(Exception):
                record = env[action.result_model].browse(action.result_res_id)
                name = record.display_name or name
            if url:
                result = {
                    "model": action.result_model,
                    "id": action.result_res_id,
                    "name": str(name)[:100],
                    "url": url,
                }
        return {
            "id": action.id,
            "tool_name": action.tool_name,
            "title": (tool or {}).get("title") or action.tool_name,
            "summary": str(preview.get("summary") or "")[:300],
            "lines": lines,
            "state": action.state,
            # a pending card of a closed conversation is shown but never actionable
            "actionable": action.state == "pending" and not closed,
            "expires_at": action.expires_at and action.expires_at.isoformat(sep=" "),
            "error": action.error or False,
            "result": result,
        }

    def _message_payload(self, env, message):
        return {
            "id": message.id,
            "role": message.role,
            "body": message.body or "",
            "date": message.create_date and message.create_date.isoformat(sep=" "),
            "run_id": message.run_id.id or False,
            "run_state": message.run_id.state or False,
            "pending_actions": [
                self._action_payload(env, a) for a in message.pending_action_ids
            ],
            "record_refs": self._refs(message.record_refs),
            "attachments": self._attachments_payload(env, message),
        }

    def _suggestions(self, env):
        """Chips for the empty state, from the tools this user can use."""
        tools = env["xtd.ai.toolbox"]._xtd_ai_visible_tools()
        chips = [
            {
                "key": tool_name,
                "text": env._(text),
                "send": send,
                "attach": attach,
            }
            for tool_name, text, send, attach in SUGGESTIONS
            if tool_name in tools
        ]
        if not chips:
            chips.append(
                {
                    "key": "help",
                    "text": env._("¿Qué cosas puedes hacer por mí?"),
                    "send": True,
                    "attach": False,
                }
            )
        return chips[:MAX_SUGGESTIONS]

    def _attachments_payload(self, env, message):
        """Attachments of a message, only those the user can read; URLs built here."""
        if "attachment_ids" not in message._fields or not message.attachment_ids:
            return []
        attachments = env["ir.attachment"].search(
            [("id", "in", message.attachment_ids.ids)], order="id"
        )
        return [
            {
                "id": a.id,
                "name": (a.name or "")[:120],
                "mimetype": a.mimetype or "",
                "size": a.file_size or 0,
                "url": f"/web/content/{a.id}?download=true",
            }
            for a in attachments
        ]

    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _settings(self, env):
        forced = env["res.users"]._xtd_ai_force_confirmation()
        return {
            "forced": forced,
            "confirm_writes": True if forced else bool(env.user.xtd_ai_confirm_writes),
        }

    # ------------------------------------------------------------------
    # routes (CONTRACT §9)
    # ------------------------------------------------------------------
    @http.route("/xtd_ai/chat/conversations", type="jsonrpc", auth="user")
    def conversations(self, limit=30):
        """History of the session user's own conversations (read-only list)."""
        env = self._env()
        limit = max(1, min(int(limit or 30), 100))
        conversations = env["xtd.ai.conversation"].search(
            [("user_id", "=", env.uid)], order="id desc", limit=limit
        )
        counts = {
            conv.id: count
            for conv, count in env["xtd.ai.message"]._read_group(
                [
                    ("conversation_id", "in", conversations.ids),
                    ("role", "in", ("user", "assistant")),
                ],
                ["conversation_id"],
                ["__count"],
            )
        }
        result = []
        for c in conversations:
            count = counts.get(c.id, 0)
            if not count and c.state != "open":
                continue  # closed and empty: nothing to read
            first = env["xtd.ai.message"].search(
                [("conversation_id", "=", c.id), ("role", "=", "user")],
                order="id",
                limit=1,
            )
            last = env["xtd.ai.message"].search(
                [
                    ("conversation_id", "=", c.id),
                    ("role", "in", ("user", "assistant")),
                ],
                order="id desc",
                limit=1,
            )
            title = " ".join((first.body or "").split())[:60] if first else ""
            if first and not title:
                files = self._attachments_payload(env, first)
                title = files[0]["name"][:60] if files else ""
            preview = " ".join((last.body or "").split())[:90] if last else ""
            if last and not preview and self._attachments_payload(env, last):
                preview = _("Adjunto")
            result.append(
                {
                    "id": c.id,
                    "name": title or _("Nueva conversación"),
                    "preview": preview,
                    "state": c.state,
                    "message_count": count,
                    "date": (c.write_date or c.create_date).isoformat(sep=" "),
                }
            )
        return result

    @http.route("/xtd_ai/chat/open", type="jsonrpc", auth="user")
    def open(self, new=False, fresh=False):
        """Return the conversation to show.

        ``new``: always close the open conversation and start another one (the
        "Nueva conversación" button). ``fresh``: the window was opened from the
        navbar icon, so start a new conversation unless the open one is empty or
        still has something in progress (a running answer or a pending action to
        confirm, which would become unconfirmable once closed). The closed one stays
        in the read-only history and is offered through the banner.
        """
        env = self._env()
        conversations = env["xtd.ai.conversation"]
        existing = conversations.search(
            [("user_id", "=", env.uid), ("state", "=", "open")], limit=1
        )
        closed_now = conversations.browse()
        if new:
            existing.action_close()
            existing = conversations.browse()
        elif fresh and existing and self._has_messages(env, existing):
            if not self._in_progress(env, existing):
                existing.action_close()
                closed_now = existing
                existing = conversations.browse()
        conversation = conversations._xtd_ai_open()
        if closed_now:
            return self._open_payload(env, conversation, closed_now.id)
        # A conversation started by itself (not by the user's request) offers a
        # read-only link to the previous one, when that one has something to read.
        previous_id = False
        if not new and not existing:
            previous = conversations.search(
                [
                    ("user_id", "=", env.uid),
                    ("state", "!=", "open"),
                    ("id", "!=", conversation.id),
                ],
                order="id desc",
                limit=5,
            )
            for candidate in previous:
                if env["xtd.ai.message"].search_count(
                    [
                        ("conversation_id", "=", candidate.id),
                        ("role", "in", ("user", "assistant")),
                    ]
                ):
                    previous_id = candidate.id
                    break
        return self._open_payload(env, conversation, previous_id)

    def _open_payload(self, env, conversation, previous_id):
        return {
            "conversation_id": conversation.id,
            "name": conversation.name,
            "settings": self._settings(env),
            "suggestions": self._suggestions(env),
            "auto_started": bool(previous_id),
            "previous_conversation_id": previous_id or False,
        }

    @staticmethod
    def _has_messages(env, conversation):
        return bool(
            env["xtd.ai.message"].search_count(
                [
                    ("conversation_id", "=", conversation.id),
                    ("role", "in", ("user", "assistant")),
                ]
            )
        )

    @staticmethod
    def _in_progress(env, conversation):
        """A running answer or a pending action that can still be confirmed."""
        running = env["xtd.ai.run"].search_count(
            [
                ("conversation_id", "=", conversation.id),
                ("state", "in", ("queued", "running")),
            ]
        )
        pending = env["xtd.ai.pending_action"].search_count(
            [
                ("conversation_id", "=", conversation.id),
                ("state", "=", "pending"),
                "|",
                ("expires_at", "=", False),
                ("expires_at", ">", fields.Datetime.now()),
            ]
        )
        return bool(running or pending)

    @http.route("/xtd_ai/chat/messages", type="jsonrpc", auth="user")
    def messages(self, conversation_id):
        env = self._env()
        conversation = self._conversation(env, conversation_id)
        messages = env["xtd.ai.message"].search(
            [("conversation_id", "=", conversation.id)],
            order="id desc",
            limit=MESSAGES_LIMIT,
        )
        messages = messages.sorted("id")
        runs = env["xtd.ai.run"].search(
            [
                ("conversation_id", "=", conversation.id),
                ("state", "in", ("queued", "running")),
            ]
        )
        return {
            "conversation_id": conversation.id,
            "state": conversation.state,
            "running_run_id": runs[:1].id or False,
            "messages": [self._message_payload(env, m) for m in messages],
        }

    @http.route("/xtd_ai/chat/send", type="jsonrpc", auth="user")
    def send(
        self, text="", conversation_id=None, company_ids=None, attachment_ids=None
    ):
        env = self._env()
        # Companies active in the web client's company switcher. jsonrpc routes do not
        # receive the web client context, so the panel sends them explicitly. Only the
        # user's own companies are kept; the gateway filters them again when minting.
        if company_ids:
            allowed = set(env.user.company_ids.ids)
            cids = [int(c) for c in company_ids if isinstance(c, int) and c in allowed]
            if cids:
                env = env(context=env.context | {"allowed_company_ids": cids})
        conversations = env["xtd.ai.conversation"]
        if conversation_id:
            conversations = self._conversation(env, conversation_id)
            if conversations.state != "open":
                # History is read-only: a closed conversation is never resumed.
                raise UserError(
                    _(
                        "Esta conversación está cerrada y es solo de lectura. "
                        "Empieza una conversación nueva para seguir preguntando."
                    )
                )
        # Raises UserError when a run is already queued/running (one at a time).
        ids = []
        for att_id in attachment_ids or []:
            if not isinstance(att_id, int) or isinstance(att_id, bool) or att_id <= 0:
                raise UserError(_("Adjunto no válido."))
            if att_id not in ids:
                ids.append(att_id)
        if len(ids) > UPLOAD_MAX_PER_MESSAGE:
            raise UserError(
                _("Máximo %s adjuntos por mensaje.", UPLOAD_MAX_PER_MESSAGE)
            )
        if ids:
            # gateway API (CONTRACT §14): validates owner, conversation, type, size
            run, token = conversations._xtd_ai_start_run(text, attachment_ids=ids)
        else:
            run, token = conversations._xtd_ai_start_run(text)
        url = os.environ.get("XTD_AI_SERVICE_URL")
        key = os.environ.get("XTD_AI_SERVICE_KEY")
        if not url:
            # Integrated mode (CONTRACT §15): the agent runs inside Odoo.
            schedule = getattr(run, "_xtd_ai_schedule", None)
            error = (
                schedule()
                if schedule
                else env._(
                    "El agente IA no está configurado: configura la clave "
                    "de Anthropic en Ajustes → Agente IA."
                )
            )
            if error:
                run._xtd_ai_fail(error)
                return {
                    "run_id": run.id,
                    "conversation_id": run.conversation_id.id,
                    "state": "failed",
                }
            return {
                "run_id": run.id,
                "conversation_id": run.conversation_id.id,
                "state": "queued",
            }
        if not key:
            run._xtd_ai_fail(
                env._(
                    "El agente IA no está configurado: falta la variable de entorno "
                    "XTD_AI_SERVICE_KEY. Avisa a tu administrador."
                )
            )
            return {
                "run_id": run.id,
                "conversation_id": run.conversation_id.id,
                "state": "failed",
            }
        body = {
            "run_id": run.id,
            "conversation_id": run.conversation_id.id,
            "db": env.cr.dbname,
            "token": token,
        }
        # The service calls back into Odoo at once: the run must be committed first.
        dbname = env.cr.dbname
        messages = {
            "rejected": env._(
                "El servicio del agente IA ha rechazado la petición (HTTP %s)."
            ),
            "unreachable": env._(
                "No se ha podido contactar con el servicio del agente IA. Inténtalo "
                "de nuevo más tarde."
            ),
        }
        env.cr.postcommit.add(lambda: _call_service(dbname, url, key, body, messages))
        return {
            "run_id": run.id,
            "conversation_id": run.conversation_id.id,
            "state": "queued",
        }

    @http.route(
        "/xtd_ai/chat/upload", type="http", auth="user", methods=["POST"], csrf=True
    )
    def upload(self, ufile=None, conversation_id=None, **kwargs):
        """Store a document for the next message (CONTRACT §14); user env, no sudo."""
        try:
            env = self._env()
            if conversation_id:
                conversation = self._conversation(env, conversation_id)
            else:
                conversation = env["xtd.ai.conversation"]._xtd_ai_open()
            if conversation.state != "open":
                raise UserError(
                    _(
                        "Esta conversación está cerrada y es solo de lectura. "
                        "No se pueden adjuntar ficheros."
                    )
                )
            if ufile is None or not hasattr(ufile, "read"):
                raise UserError(_("No se ha recibido ningún fichero."))
            data = ufile.read(UPLOAD_MAX_BYTES + 1)
            if len(data) > UPLOAD_MAX_BYTES:
                raise UserError(_("El fichero supera el máximo de 10 MB."))
            if not data:
                raise UserError(_("El fichero está vacío."))
            mimetype = _sniff_mimetype(data)
            name = os.path.basename((ufile.filename or "").replace("\\", "/")).strip()
            name = (name or _("adjunto"))[:120]
            extensions = UPLOAD_TYPES.get(mimetype)
            if not extensions or not name.lower().endswith(extensions):
                raise UserError(
                    _("Tipo de fichero no admitido. Solo PDF, PNG, JPEG o WebP.")
                )
            attachment = env["ir.attachment"].create(
                {
                    "name": name,
                    "raw": data,
                    "mimetype": mimetype,
                    "res_model": "xtd.ai.conversation",
                    "res_id": conversation.id,
                }
            )
        except AccessError as exc:
            return self._json({"error": str(exc.args[0])}, status=403)
        except UserError as exc:
            return self._json({"error": str(exc.args[0])}, status=400)
        return self._json(
            {
                "attachment_id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "size": len(data),
            }
        )

    @http.route("/xtd_ai/chat/pending/confirm", type="jsonrpc", auth="user")
    def pending_confirm(self, action_id):
        env = self._env()
        action = self._pending(env, action_id)
        result = action.action_confirm()
        return {
            "state": result["state"],
            "error": result["error"],
            "action": self._action_payload(env, action),
        }

    @http.route("/xtd_ai/chat/pending/cancel", type="jsonrpc", auth="user")
    def pending_cancel(self, action_id):
        env = self._env()
        action = self._pending(env, action_id)
        action.action_cancel()
        return {"state": "cancelled", "action": self._action_payload(env, action)}

    def _pending(self, env, action_id):
        action = env["xtd.ai.pending_action"].search(
            [("id", "=", int(action_id or 0)), ("user_id", "=", env.uid)]
        )
        if not action:
            raise AccessError(_("Esta acción no es tuya."))
        if action.conversation_id.state != "open":
            raise UserError(
                _(
                    "Esta acción pertenece a una conversación cerrada y ya no se puede "
                    "confirmar ni cancelar. Pídele al agente que la prepare de nuevo."
                )
            )
        return action

    @http.route("/xtd_ai/chat/run/cancel", type="jsonrpc", auth="user")
    def run_cancel(self, run_id):
        env = self._env()
        run = env["xtd.ai.run"].search(
            [("id", "=", int(run_id or 0)), ("user_id", "=", env.uid)]
        )
        if not run:
            raise AccessError(_("Esta ejecución no es tuya."))
        run.action_cancel()
        return {"state": "cancelled"}

    @http.route("/xtd_ai/chat/settings", type="jsonrpc", auth="user")
    def settings(self, confirm_writes=None):
        env = self._env()
        if (
            confirm_writes is not None
            and not env["res.users"]._xtd_ai_force_confirmation()
        ):
            env.user.write({"xtd_ai_confirm_writes": bool(confirm_writes)})
        return self._settings(env)

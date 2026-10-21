import logging
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..tools.errors import XtdAiDraftOnlyError, XtdAiToolError
from ..tools.schema import validate

_logger = logging.getLogger(__name__)

EXPIRY_HOURS = 24


class XtdAiPendingAction(models.Model):
    _name = "xtd.ai.pending_action"
    _description = "AI agent pending action"
    _order = "id desc"

    run_id = fields.Many2one(
        "xtd.ai.run", required=True, ondelete="cascade", index=True
    )
    conversation_id = fields.Many2one(
        "xtd.ai.conversation", required=True, ondelete="cascade", index=True
    )
    user_id = fields.Many2one(
        "res.users", required=True, ondelete="cascade", index=True
    )
    message_id = fields.Many2one("xtd.ai.message", ondelete="set null", index=True)
    tool_name = fields.Char(required=True)
    arguments = fields.Json()
    preview = fields.Json()
    cids = fields.Json(
        help="Allowed company ids at the time the agent proposed the action."
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
            ("failed", "Failed"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    result_model = fields.Char()
    result_res_id = fields.Integer()
    error = fields.Char()
    expires_at = fields.Datetime(
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=EXPIRY_HOURS),
    )

    # ------------------------------------------------------------------
    # Public API for the chat routes: they run as the session user
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Execute the pending action as the session user.

        Needs a web session of the owner: it can never be reached with the AI
        token (the token only works on ``/xtd_ai/*`` routes), and it refuses to
        run inside an AI run context.

        :returns: dict ``{"state", "records", "error"}``. Business failures
            (permissions, validation, guards) do not raise: the action is
            marked ``failed`` and the error is returned, so it persists.
        :raises: ``AccessError`` (not the owner), ``UserError`` (not pending
            or expired).
        """
        self.ensure_one()
        action = self._xtd_ai_check_actor()
        action.lock_for_update()
        action.invalidate_recordset()
        if action.state != "pending":
            raise UserError(_("Esta acción ya no está pendiente."))
        if action.expires_at and action.expires_at < fields.Datetime.now():
            raise UserError(
                _("Esta acción ha caducado. Pídele al agente que la prepare de nuevo.")
            )

        started = time.monotonic()
        user = self.env.user
        toolbox = self.env["xtd.ai.toolbox"]
        tool = toolbox._xtd_ai_tools().get(action.tool_name)
        refs, error, code = [], None, None
        try:
            if tool is None or not toolbox._xtd_ai_tool_visible(tool):
                raise XtdAiToolError(
                    "not_found", _("La herramienta ya no está disponible.")
                )
            if tool["kind"] == "read":
                raise XtdAiToolError("validation", _("Acción no válida."))
            cids = [c for c in (action.cids or []) if isinstance(c, int)]
            if not cids or not set(cids) <= set(user.company_ids.ids):
                raise AccessError(_("Compañía no permitida."))
            context = toolbox._xtd_ai_exec_context(
                action.run_id.id, cids, user.lang, user.tz
            )
            env = self.env(context=context)
            toolbox_env = env["xtd.ai.toolbox"]
            args = action.arguments or {}
            errors = validate(toolbox_env._xtd_ai_schema(tool), args)
            if errors:
                raise XtdAiToolError("validation", "; ".join(errors[:5]))
            result = toolbox_env._xtd_ai_execute(tool, args)
            refs = result["records"]
        except XtdAiDraftOnlyError as exc:
            error, code = str(exc), "draft_only"
        except AccessError as exc:
            error, code = str(exc), "access_denied"
        except XtdAiToolError as exc:
            error, code = exc.message, exc.code
        except UserError as exc:
            error, code = str(exc), "validation"
        except Exception:
            _logger.exception("Confirmation of pending action %s failed", action.id)
            error, code = _("Error interno al ejecutar la acción."), "internal"

        # sudo: users have read-only ACL on pending actions and audit.
        action_su = action.sudo()
        vals = (
            {"state": "failed", "error": (error or "")[:250]}
            if error
            else {"state": "confirmed"}
        )
        if refs and not error:
            vals.update(result_model=refs[0]["model"], result_res_id=refs[0]["id"])
        action_su.write(vals)
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "guard_blocked" if code == "draft_only" else "confirm",
            "denied"
            if code in ("draft_only", "access_denied")
            else ("error" if error else "ok"),
            run_id=action.run_id.id,
            user_id=user.id,
            company_id=self.env.company.id,
            tool_name=action.tool_name,
            arguments=action.arguments,
            error_code=code,
            record_refs=refs,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        if action.run_id.sudo().conversation_id:
            action_su.run_id._xtd_ai_notify(action_su.message_id)
        return {"state": action_su.state, "records": refs, "error": error}

    def action_cancel(self):
        """Cancel a pending action of the session user."""
        self.ensure_one()
        action = self._xtd_ai_check_actor()
        action.lock_for_update()
        action.invalidate_recordset()
        if action.state != "pending":
            raise UserError(_("Esta acción ya no está pendiente."))
        action.sudo().write({"state": "cancelled"})
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "cancel",
            "ok",
            run_id=action.run_id.id,
            user_id=self.env.uid,
            company_id=self.env.company.id,
            tool_name=action.tool_name,
            arguments=action.arguments,
        )
        action.sudo().run_id._xtd_ai_notify(action.sudo().message_id)
        return {"state": "cancelled"}

    def _xtd_ai_check_actor(self):
        if self.env.context.get("xtd_ai_run"):
            raise AccessError(_("Operación no permitida desde el agente."))
        if self.env.su:
            raise AccessError(_("Operación no permitida en modo superusuario."))
        # The record rule already hides other users' actions; check explicitly anyway.
        action = self
        if action.user_id.id != self.env.uid:
            raise AccessError(_("Esta acción no es tuya."))
        if not self.env.user.has_group("xtd_ai_gateway.group_xtd_ai_user"):
            raise AccessError(_("No tienes acceso al agente IA."))
        return action

    # ------------------------------------------------------------------
    def _xtd_ai_history_notes(self):
        """Lines such as ``[Acción #12: creada S00042]`` for the LLM history."""
        notes = []
        for action in self.sudo():
            if action.state == "confirmed":
                label = _("creada")
                if action.result_model and action.result_res_id:
                    record = (
                        self.env[action.result_model]
                        .sudo()
                        .browse(action.result_res_id)
                    )
                    if record.exists():
                        label = _("creada %s", (record.display_name or "")[:60])
            else:
                label = {
                    "pending": _("pendiente de confirmación"),
                    "cancelled": _("cancelada"),
                    "expired": _("caducada"),
                    "failed": _("fallida"),
                }[action.state]
            notes.append(f"[Acción #{action.id}: {label}]")
        return "\n".join(notes)

    @api.model
    def _xtd_ai_expire_old(self):
        old = self.search(
            [("state", "=", "pending"), ("expires_at", "<", fields.Datetime.now())]
        )
        old.write({"state": "expired"})

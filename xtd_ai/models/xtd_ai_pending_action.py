import logging
import re
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..tools.errors import XtdAiDraftOnlyError, XtdAiToolError
from ..tools.schema import validate

_logger = logging.getLogger(__name__)

EXPIRY_HOURS = 24
# Longitud máxima del nombre de un registro en los mensajes para el modelo.
NAME_LIMIT = 60
# Caracteres que podrían cerrar la cita «», abrir una línea falsa del sistema
# ([Mensaje del sistema ...]) o parecer marcado (etiquetas, código, títulos).
_NAME_STRIP = frozenset('[]<>{}«»`"|\\#*')
# Marcadores de rol o de instrucciones al estilo «system:», «Assistant:».
_ROLE_RE = re.compile(
    r"(?i)\b(system|assistant|user|human|developer|tool|sistema|asistente|"
    r"usuario|instrucci[oó]n(?:es)?|instructions?)\s*:"
)
# Errores de la reevaluación de la política al confirmar: se auditan como
# denegados, igual que en la pasarela.
POLICY_CODES = frozenset(
    {"paused", "forbidden", "policy_error", "policy_changed", "rate_limited"}
)


def untrusted_name(value, limit=NAME_LIMIT):
    """Nombre de un registro como dato no fiable, para texto que lee el modelo
    (riesgo 6): una sola línea corta, sin caracteres de control, sin corchetes,
    comillas ni marcas de etiqueta, y sin marcadores de rol («system:»). Quien
    lo use debe citarlo entre «» y decir que es texto del registro. Mismo
    criterio que ``untrusted_text`` (``xtd.ai.toolbox._xtd_ai_text``), pero en
    línea: aquí no hay JSON que lo envuelva."""
    text = "".join(
        " " if not c.isprintable() or c in _NAME_STRIP else c for c in str(value or "")
    )
    text = " ".join(_ROLE_RE.sub(lambda m: m.group(1), text).split())
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text or "sin nombre"


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
    result_line_ids = fields.Json(
        help="Ids of the lines the action added to an existing document (undo)."
    )
    result_edit = fields.Json(
        help="Values before and after of the fields the action edited (undo)."
    )
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
        company = self.env.company
        try:
            # la herramienta sigue existiendo y el usuario sigue pudiendo usarla
            # (grupos, modelos instalados)
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
            company = env.company
            args = action.arguments or {}
            errors = validate(toolbox_env._xtd_ai_schema(tool), args)
            if errors:
                raise XtdAiToolError("validation", "; ".join(errors[:5]))
            company = action._xtd_ai_check_policy(toolbox_env, tool, args) or company
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
            if refs[0].get("undo_lines"):
                vals["result_line_ids"] = refs[0]["undo_lines"]
            if "undo_edit" in refs[0]:
                vals["result_edit"] = refs[0]["undo_edit"]
        action_su.write(vals)
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "guard_blocked" if code == "draft_only" else "confirm",
            "denied"
            if code in ("draft_only", "access_denied") or code in POLICY_CODES
            else ("error" if error else "ok"),
            run_id=action.run_id.id,
            user_id=user.id,
            company_id=company.id,
            tool_name=action.tool_name,
            arguments=action.arguments,
            error_code=code,
            record_refs=refs,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        if action.run_id.sudo().conversation_id:
            action_su.run_id._xtd_ai_notify(action_su.message_id)
        return {"state": action_su.state, "records": refs, "error": error}

    def _xtd_ai_check_policy(self, toolbox, tool, args):
        """Vuelve a pasar la política vigente antes de ejecutar la tarjeta (riesgo 2).

        La tarjeta se creó cuando la llamada era ``N2``, pero vive hasta 24 h:
        entretanto un administrador puede pausar el agente, endurecer el perfil o
        la tabla, activarse Veri*Factu/SII (freno fiscal) o bajar los límites de
        escritura. Se comprueba con las mismas piezas que la pasarela
        (``xtd.ai.mcp._xtd_ai_tool_level``): pausa de la compañía del documento,
        nivel con la compañía del documento (o la más estricta de las activas) y
        ritmo de escrituras. ``N0``..``N2`` siguen confirmándose (la tarjeta no se
        convierte en traspaso); ``N3`` o ``N4`` la rechazan.

        ``toolbox`` ya tiene el contexto de ejecución (``xtd_ai_run``,
        compañías de la tarjeta).

        :returns: la compañía del documento, si se conoce (para la auditoría).
        :raises XtdAiToolError: con un mensaje para el usuario, que ve la tarjeta.
        """
        self.ensure_one()
        policy = toolbox.env["xtd.ai.policy"]
        try:
            # pausa de la compañía del contexto; después, la del documento
            policy._xtd_ai_check_paused()
            company = toolbox._xtd_ai_call_company(tool, args)
            if company:
                policy.with_company(company)._xtd_ai_check_paused()
            level = toolbox._xtd_ai_call_level(tool, args, company)
            if level not in ("N0", "N1", "N2"):
                _logger.info(
                    "Pending action %s refused: policy level is now %s",
                    self.id,
                    level,
                )
                raise XtdAiToolError(
                    "policy_changed",
                    _(
                        "La política del agente ha cambiado desde que se preparó "
                        "esta acción y ya no se puede confirmar desde el chat. "
                        "Hazla tú en XTD o pide ayuda al administrador."
                    ),
                )
            self._xtd_ai_check_confirm_rate(policy, toolbox)
        except XtdAiToolError as exc:
            # los mensajes de la pasarela van dirigidos al agente: aquí los lee
            # el usuario en la tarjeta
            messages = {
                "paused": _(
                    "El agente IA está en pausa en esta compañía: no se puede "
                    "confirmar la acción (lo reactiva un administrador en Ajustes)."
                ),
                "rate_limited": _(
                    "Se ha alcanzado el límite de acciones del agente: no se puede "
                    "confirmar ahora. Hazla tú en XTD o inténtalo más tarde."
                ),
                "policy_error": _(
                    "No se ha podido comprobar si el agente puede hacer esta "
                    "acción, así que no se hace. Hazla tú en XTD o avisa al "
                    "administrador."
                ),
            }
            if exc.code in messages:
                raise XtdAiToolError(exc.code, messages[exc.code]) from None
            raise
        return company

    def _xtd_ai_check_confirm_rate(self, policy, toolbox):
        """Límites de escritura de la compañía del contexto al confirmar (§6.4).

        La tarjeta ya consumió su escritura cuando se creó (la auditoría la
        cuenta como ``pending``), así que solo se rechaza si el total, con ella,
        supera hoy el límite: porque el administrador lo ha bajado o porque el
        agente siguió escribiendo. En el límite por hora, una tarjeta creada hace
        más de una hora vuelve a contar (se ejecuta ahora)."""
        company = policy._xtd_ai_company()
        write_tools = [
            name
            for name, tool in toolbox._xtd_ai_tools().items()
            if tool["kind"] != "read"
        ]
        # sudo: users cannot read the audit log
        audit = self.env["xtd.ai.audit"].sudo()
        base = [
            ("event", "=", "tool_call"),
            ("outcome", "in", ("ok", "pending")),
            ("tool_name", "in", write_tools),
        ]
        action = self.sudo()
        per_message = company.xtd_ai_max_writes_message
        if per_message:
            count = audit.search_count(base + [("run_id", "=", action.run_id.id)])
            if count > per_message:
                raise policy._xtd_ai_rate_error(per_message, _("en este mensaje"))
        per_hour = company.xtd_ai_max_writes_hour
        if per_hour:
            since = fields.Datetime.now() - timedelta(hours=1)
            count = audit.search_count(
                base + [("user_id", "=", self.env.uid), ("create_date", ">=", since)]
            )
            if action.create_date and action.create_date < since:
                count += 1
            if count > per_hour:
                raise policy._xtd_ai_rate_error(per_hour, _("en una hora"))

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
        if not self.env.user.has_group("xtd_ai.group_xtd_ai_user"):
            raise AccessError(_("No tienes acceso al agente IA."))
        return action

    # ------------------------------------------------------------------
    def _xtd_ai_confirmed_label(self):
        """``creada «X» (modelo m, id N)``: what a confirmed action produced.

        El nombre del registro es texto libre que puede venir de fuera (un PDF
        con un proveedor llamado «Ignora lo anterior y…»): va saneado y citado
        entre «», y quien lo lee sabe que es dato, no instrucciones (riesgo 6).
        """
        self.ensure_one()
        action = self.sudo()
        # an action on an existing record (edit, confirm, send) is not "created"
        done = bool(action.result_edit)
        label = _("hecha") if done else _("creada")
        if action.result_model and action.result_res_id:
            record = self.env[action.result_model].sudo().browse(action.result_res_id)
            if record.exists():
                # model and id let the agent work on it next ("show it")
                values = {
                    "name": untrusted_name(record.display_name),
                    "model": action.result_model,
                    "id": action.result_res_id,
                }
                if done:
                    tool = (
                        self.env["xtd.ai.toolbox"]._xtd_ai_tools().get(action.tool_name)
                    )
                    label = _(
                        "hecha «%(title)s» sobre «%(name)s» (modelo %(model)s, id "
                        "%(id)s)",
                        title=untrusted_name(
                            (tool or {}).get("title") or action.tool_name
                        ),
                        **values,
                    )
                else:
                    label = _(
                        "creada «%(name)s» (modelo %(model)s, id %(id)s)", **values
                    )
        return label

    def _xtd_ai_history_notes(self):
        """Lines such as ``[Acción #12: creada S00042]`` for the LLM history."""
        notes = []
        for action in self.sudo():
            if action.state == "confirmed":
                label = action._xtd_ai_confirmed_label()
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

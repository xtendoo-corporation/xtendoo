"""Internal notes and activities on the records the registry allows (§4 CRM,
Proyectos): ``log_note``, ``schedule_activity``, ``complete_activity`` and
``my_activities``.

Everything stays inside the company: a note is an internal note (never a
message to followers or an email) and activities notify nobody by email. The
models come from ``xtd.ai.record.registry`` (spec key ``chatter``) and the
user's own ORM rights decide on which records.
"""

from datetime import date, timedelta

from odoo import fields, models
from odoo.tools import plaintext2html

from ..tools import unlock, xtd_ai_tool
from ..tools.errors import XtdAiToolError
from .xtd_ai_policy import max_level

ACTIVITY_TYPES = {
    "call": "mail.mail_activity_data_call",
    "meeting": "mail.mail_activity_data_meeting",
    "todo": "mail.mail_activity_data_todo",
}
NOTE_LIMIT = 2000


def _models_enum(toolbox):
    return toolbox.env["xtd.ai.record.registry"]._xtd_ai_chatter_models() or [
        "crm.lead"
    ]


def _note_schema(toolbox):
    return {
        "type": "object",
        "properties": {
            "model": {"type": "string", "enum": _models_enum(toolbox)},
            "record": {"type": "string", "description": "Id del registro."},
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": NOTE_LIMIT,
                "description": "Texto de la nota interna, en texto plano.",
            },
        },
        "required": ["model", "record", "text"],
        "additionalProperties": False,
    }


def _schedule_schema(toolbox):
    return {
        "type": "object",
        "properties": {
            "model": {"type": "string", "enum": _models_enum(toolbox)},
            "record": {"type": "string", "description": "Id del registro."},
            "activity_type": {
                "type": "string",
                "enum": sorted(ACTIVITY_TYPES),
                "description": "call = llamada, meeting = reunión, todo = tarea.",
            },
            "date_deadline": {
                "type": "string",
                "format": "date",
                "description": "Fecha límite AAAA-MM-DD (hoy si se omite).",
            },
            "summary": {
                "type": "string",
                "maxLength": 200,
                "description": "Resumen corto («Llamar para cerrar precio»).",
            },
            "note": {
                "type": "string",
                "maxLength": NOTE_LIMIT,
                "description": "Detalle en texto plano (opcional).",
            },
            "assigned_to": {
                "type": "string",
                "maxLength": 200,
                "description": (
                    "Usuario interno responsable (id o nombre). Omítelo: es el "
                    "propio usuario."
                ),
            },
        },
        "required": ["model", "record", "activity_type"],
        "additionalProperties": False,
    }


class XtdAiToolboxChatter(models.AbstractModel):
    _name = "xtd.ai.toolbox.chatter"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: internal notes and activities"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _xtd_ai_chatter_record(self, model, name_or_id):
        registry = self.env["xtd.ai.record.registry"]
        if model not in registry._xtd_ai_chatter_models():
            raise XtdAiToolError(
                "forbidden",
                self.env._("No se pueden añadir notas ni actividades a «%s».", model),
            )
        record = self._xtd_ai_resolve(model, name_or_id)
        record.check_access("write")
        return record

    def _xtd_ai_chatter_level(self, model, name_or_id):
        registry = self.env["xtd.ai.record.registry"]
        record = self._xtd_ai_chatter_record(model, name_or_id)
        level = self.env["xtd.ai.policy"]._xtd_ai_level("edit_low")
        if registry._xtd_ai_is_external(model, record):
            level = max_level(level, "N2")
        return level

    def _xtd_ai_chatter_ref(self, record):
        # an edit without values: the chat offers no "Deshacer" for it, and
        # the record is never taken for one the agent created
        return self._xtd_ai_ref(record) | {"undo_edit": {"before": {}, "after": {}}}

    def _xtd_ai_assignee(self, value):
        if value in (None, ""):
            return self.env.user
        return self._xtd_ai_resolve(
            "res.users", value, domain=[("share", "=", False), ("active", "=", True)]
        )

    def _xtd_ai_deadline(self, value):
        if not value:
            return fields.Date.context_today(self)
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            raise XtdAiToolError(
                "validation", self.env._("Fecha en formato AAAA-MM-DD.")
            ) from None

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="log_note",
        title="Nota interna",
        description=(
            "Deja una nota INTERNA en el historial (chatter) de una oportunidad o "
            "tarea: solo la ve el personal de la empresa, no se envía a nadie. "
            "Úsala para «apunta que…», «deja anotado…». Nunca para escribir al "
            "cliente."
        ),
        input_schema=_note_schema,
        kind="draft",
        preview="_xtd_ai_preview_log_note",
        policy="_xtd_ai_policy_log_note",
        visible="_xtd_ai_visible_chatter",
        unlocks=("*.message_post",),
    )
    def tool_log_note(self, args):
        record = self._xtd_ai_chatter_record(args["model"], args["record"])
        text = (args.get("text") or "").strip()
        if not text:
            raise XtdAiToolError("validation", self.env._("La nota está vacía."))
        message = unlock(record, "message_post").message_post(
            body=plaintext2html(text[:NOTE_LIMIT]),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "data": {"model": record._name, "id": record.id, "note_id": message.id},
            "records": [self._xtd_ai_chatter_ref(record)],
        }

    def _xtd_ai_visible_chatter(self):
        return bool(self.env["xtd.ai.record.registry"]._xtd_ai_chatter_models())

    def _xtd_ai_policy_log_note(self, args):
        return self._xtd_ai_chatter_level(args["model"], args["record"])

    def _xtd_ai_preview_log_note(self, args):
        record = self._xtd_ai_chatter_record(args["model"], args["record"])
        return {
            "summary": self.env._(
                "Nota interna en «%s»", (record.display_name or "")[:80]
            ),
            "lines": [
                {
                    "field": self.env._("Nota"),
                    "value": self._xtd_ai_text(args.get("text")),
                }
            ],
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="schedule_activity",
        title="Programar actividad",
        description=(
            "Programa una actividad (llamada, reunión o tarea pendiente) en una "
            "oportunidad o tarea, con fecha límite y resumen. Por defecto para el "
            "propio usuario; se le puede asignar a otro usuario interno. No envía "
            "correos ni invitaciones."
        ),
        input_schema=_schedule_schema,
        kind="draft",
        preview="_xtd_ai_preview_schedule_activity",
        policy="_xtd_ai_policy_schedule_activity",
        visible="_xtd_ai_visible_chatter",
    )
    def tool_schedule_activity(self, args):
        record = self._xtd_ai_chatter_record(args["model"], args["record"])
        user = self._xtd_ai_assignee(args.get("assigned_to"))
        activity_type = self.env.ref(ACTIVITY_TYPES[args["activity_type"]])
        # quick_update: the assignee sees it in their activities, no email
        activity = record.with_context(
            mail_activity_quick_update=True
        ).activity_schedule(
            activity_type_id=activity_type.id,
            date_deadline=self._xtd_ai_deadline(args.get("date_deadline")),
            summary=(args.get("summary") or "").strip()[:200],
            note=plaintext2html(args["note"][:NOTE_LIMIT]) if args.get("note") else "",
            user_id=user.id,
        )
        return {
            "data": {
                "model": record._name,
                "id": record.id,
                "activity_id": activity.id,
                "type": activity_type.name,
                "date_deadline": str(activity.date_deadline),
                "assigned_to": user.name,
            },
            "records": [self._xtd_ai_chatter_ref(record)],
        }

    def _xtd_ai_policy_schedule_activity(self, args):
        self._xtd_ai_assignee(args.get("assigned_to"))
        return self._xtd_ai_chatter_level(args["model"], args["record"])

    def _xtd_ai_preview_schedule_activity(self, args):
        record = self._xtd_ai_chatter_record(args["model"], args["record"])
        user = self._xtd_ai_assignee(args.get("assigned_to"))
        activity_type = self.env.ref(ACTIVITY_TYPES[args["activity_type"]])
        deadline = self._xtd_ai_deadline(args.get("date_deadline"))
        lines = [
            {"field": self.env._("Tipo"), "value": activity_type.name},
            {"field": self.env._("Fecha"), "value": str(deadline)},
            {"field": self.env._("Responsable"), "value": user.name},
        ]
        if args.get("summary"):
            lines.append(
                {
                    "field": self.env._("Resumen"),
                    "value": self._xtd_ai_text(args["summary"]),
                }
            )
        return {
            "summary": self.env._(
                "%(type)s en «%(name)s» para el %(date)s",
                type=activity_type.name,
                name=(record.display_name or "")[:80],
                date=deadline,
            ),
            "lines": lines,
        }

    # ------------------------------------------------------------------
    def _xtd_ai_activity(self, activity_id):
        registry = self.env["xtd.ai.record.registry"]
        activity = self.env["mail.activity"].search(
            [
                ("id", "=", int(activity_id)),
                ("res_model", "in", registry._xtd_ai_chatter_models()),
            ],
            limit=1,
        )
        if not activity:
            raise XtdAiToolError(
                "not_found",
                self.env._("No se ha encontrado la actividad %s.", activity_id),
            )
        record = self.env[activity.res_model].browse(activity.res_id)
        if activity.user_id != self.env.user:
            record.check_access("write")
        return activity, record

    @xtd_ai_tool(
        name="complete_activity",
        title="Marcar actividad como hecha",
        description=(
            "Marca como hecha una actividad (id de my_activities, get_opportunity "
            "o get_task), con un comentario opcional de lo que se hizo. Queda en "
            "el historial interno; no se envía a nadie."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "Id de la actividad.",
                },
                "feedback": {
                    "type": "string",
                    "maxLength": NOTE_LIMIT,
                    "description": "Qué se hizo, en texto plano (opcional).",
                },
            },
            "required": ["activity_id"],
            "additionalProperties": False,
        },
        kind="draft",
        preview="_xtd_ai_preview_complete_activity",
        policy="_xtd_ai_policy_complete_activity",
        visible="_xtd_ai_visible_chatter",
    )
    def tool_complete_activity(self, args):
        activity, record = self._xtd_ai_activity(args["activity_id"])
        summary = activity.summary or activity.activity_type_id.name
        activity.action_feedback(feedback=(args.get("feedback") or "")[:NOTE_LIMIT])
        return {
            "data": {
                "model": record._name,
                "id": record.id,
                "done": self._xtd_ai_text(summary),
            },
            "records": [self._xtd_ai_chatter_ref(record)],
        }

    def _xtd_ai_policy_complete_activity(self, args):
        activity, record = self._xtd_ai_activity(args["activity_id"])
        return self._xtd_ai_chatter_level(record._name, str(record.id))

    def _xtd_ai_preview_complete_activity(self, args):
        activity, record = self._xtd_ai_activity(args["activity_id"])
        return {
            "summary": self.env._(
                "Marcar como hecha «%(activity)s» en «%(name)s»",
                activity=(activity.summary or activity.activity_type_id.name or "")[
                    :80
                ],
                name=(record.display_name or "")[:80],
            ),
            "lines": [
                {
                    "field": self.env._("Comentario"),
                    "value": self._xtd_ai_text(args.get("feedback") or "—"),
                }
            ],
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="my_activities",
        title="Mis actividades",
        description=(
            "Lista las actividades pendientes del usuario (llamadas, reuniones, "
            "tareas) en oportunidades y tareas: vencidas, de hoy o de los próximos "
            "días. Devuelve el id de cada actividad (para complete_activity) y su "
            "registro. No modifica datos."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "when": {
                    "type": "string",
                    "enum": ["overdue", "today", "week", "all"],
                    "description": (
                        "overdue = vencidas, today = hoy y vencidas (por defecto), "
                        "week = próximos 7 días y vencidas, all = todas."
                    ),
                },
            },
            "required": [],
            "additionalProperties": False,
        },
        kind="read",
        visible="_xtd_ai_visible_chatter",
    )
    def tool_my_activities(self, args):
        registry = self.env["xtd.ai.record.registry"]
        today = fields.Date.context_today(self)
        domain = [
            ("user_id", "=", self.env.uid),
            ("res_model", "in", registry._xtd_ai_chatter_models()),
        ]
        when = args.get("when") or "today"
        if when == "overdue":
            domain.append(("date_deadline", "<", today))
        elif when == "today":
            domain.append(("date_deadline", "<=", today))
        elif when == "week":
            domain.append(("date_deadline", "<=", today + timedelta(days=7)))
        found = self.env["mail.activity"].search(
            domain, limit=self._xtd_ai_limit(None), order="date_deadline, id"
        )
        rows = [
            {
                "activity_id": act.id,
                "type": act.activity_type_id.name or None,
                "summary": self._xtd_ai_text(act.summary),
                "date_deadline": str(act.date_deadline),
                "overdue": act.date_deadline < today,
                "record": {
                    "model": act.res_model,
                    "id": act.res_id,
                    "name": self._xtd_ai_text(act.res_name),
                },
            }
            for act in found
        ]
        return {"data": self._xtd_ai_list(rows), "records": []}

    def _xtd_ai_activity_rows(self, record):
        """Open activities of ``record`` for the get_* tools of the bridges."""
        return [
            {
                "activity_id": act.id,
                "type": act.activity_type_id.name or None,
                "summary": self._xtd_ai_text(act.summary),
                "date_deadline": str(act.date_deadline),
                "assigned_to": act.user_id.name or None,
            }
            for act in record.activity_ids[:20]
        ]

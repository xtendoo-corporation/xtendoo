from datetime import date, timedelta

from odoo import fields, models
from odoo.tools import html2plaintext

from odoo.addons.xtd_ai.tools import XtdAiToolError, xtd_ai_tool

PROJECT_GROUPS = ["project.group_project_user"]
TIMESHEET_GROUPS = ["hr_timesheet.group_hr_timesheet_user"]


def _schema(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required or []),
        "additionalProperties": False,
    }


_DATE = {"type": "string", "format": "date"}


class XtdAiToolboxProject(models.AbstractModel):
    _name = "xtd.ai.toolbox.project"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: tasks and own timesheets"

    _xtd_ai_skills = {"proyectos": "data/skills/proyectos.md"}

    # ------------------------------------------------------------------
    def _xtd_ai_taint_tasks(self, tasks):
        external = self.env["xtd.ai.record.registry"]._xtd_ai_is_external(
            "project.task", tasks
        )
        if external:
            self._xtd_ai_mark_external()
        return external

    def _xtd_ai_task_row(self, task):
        return {
            "id": task.id,
            "name": self._xtd_ai_text(task.name),
            "project": {"id": task.project_id.id, "name": task.project_id.name}
            if task.project_id
            else None,
            "stage": {"id": task.stage_id.id, "name": task.stage_id.name}
            if task.stage_id
            else None,
            "date_deadline": str(task.date_deadline.date())
            if task.date_deadline
            else None,
            "assignees": task.user_ids.mapped("name"),
            "allocated_hours": task.allocated_hours,
            "effective_hours": task.effective_hours
            if "effective_hours" in task._fields
            else None,
        }

    def _xtd_ai_line_row(self, line):
        return {
            "id": line.id,
            "date": str(line.date),
            "hours": line.unit_amount,
            "description": self._xtd_ai_text(line.name),
            "project": line.project_id.name or None,
            "task": {
                "id": line.task_id.id,
                "name": self._xtd_ai_text(line.task_id.name),
            }
            if line.task_id
            else None,
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="search_tasks",
        title="Buscar tareas",
        description=(
            "Lista tareas de proyecto: por defecto las asignadas al usuario y "
            "abiertas. Filtros: proyecto, etapa, texto del nombre e incluir las "
            "cerradas. Devuelve id, proyecto, etapa, fecha límite, asignados y "
            "horas previstas e imputadas. No modifica datos."
        ),
        input_schema=_schema(
            {
                "project": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Proyecto (id o nombre).",
                },
                "stage": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Etapa (nombre).",
                },
                "text": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Texto que contiene el nombre de la tarea.",
                },
                "mine": {
                    "type": "boolean",
                    "description": "Solo las asignadas al usuario (true por defecto).",
                },
                "include_closed": {
                    "type": "boolean",
                    "description": "Incluir hechas y canceladas (false por defecto).",
                },
            }
        ),
        kind="read",
        skill="proyectos",
        groups=PROJECT_GROUPS,
    )
    def tool_search_tasks(self, args):
        domain = [("project_id", "!=", False)]
        if args.get("mine", True):
            domain.append(("user_ids", "in", self.env.uid))
        if not args.get("include_closed"):
            domain.append(("state", "not in", ("1_done", "1_canceled")))
        if args.get("project"):
            project = self._xtd_ai_resolve("project.project", args["project"])
            domain.append(("project_id", "=", project.id))
        if args.get("stage"):
            domain.append(("stage_id.name", "ilike", args["stage"]))
        if args.get("text"):
            domain.append(("name", "ilike", args["text"]))
        limit = self._xtd_ai_limit(None)
        tasks = self.env["project.task"].search(
            domain, limit=limit, order="date_deadline asc, priority desc, id desc"
        )
        total = (
            self.env["project.task"].search_count(domain)
            if len(tasks) >= limit
            else len(tasks)
        )
        # names only: get_task (full text) is what brakes the run
        rows = [self._xtd_ai_task_row(task) for task in tasks]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": tasks}

    @xtd_ai_tool(
        name="get_task",
        title="Detalle de una tarea",
        description=(
            "Detalle de una tarea: proyecto, etapa, etapas posibles de su "
            "proyecto, fechas, descripción, actividades pendientes (con su id) y "
            "las horas imputadas por el propio usuario. No modifica datos."
        ),
        input_schema=_schema(
            {
                "task": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Id (preferible) o nombre de la tarea.",
                }
            },
            ["task"],
        ),
        kind="read",
        skill="proyectos",
        groups=PROJECT_GROUPS,
    )
    def tool_get_task(self, args):
        task = self._xtd_ai_resolve(
            "project.task", args["task"], domain=[("project_id", "!=", False)]
        )
        data = self._xtd_ai_task_row(task)
        own_lines = self.env["account.analytic.line"].search(
            [("task_id", "=", task.id), ("user_id", "=", self.env.uid)],
            order="date desc",
            limit=20,
        )
        data.update(
            {
                "description": self._xtd_ai_text(
                    html2plaintext(task.description or "").strip() or None
                ),
                "tags": task.tag_ids.mapped("name"),
                "project_stages": [
                    {"id": s.id, "name": s.name} for s in task.project_id.type_ids
                ],
                "activities": self.env["xtd.ai.toolbox.chatter"]._xtd_ai_activity_rows(
                    task
                ),
                "my_timesheets": [self._xtd_ai_line_row(line) for line in own_lines],
                "external_text": self._xtd_ai_taint_tasks(task),
            }
        )
        return {"data": data, "records": task}

    @xtd_ai_tool(
        name="my_timesheets",
        title="Mis partes de horas",
        description=(
            "Partes de horas del PROPIO usuario en un rango de fechas (por defecto "
            "esta semana): líneas con id (para corregirlas con update_record), "
            "fecha, horas, proyecto y tarea, y el total. No modifica datos."
        ),
        input_schema=_schema(
            {
                "date_from": _DATE | {"description": "Desde (incluida), AAAA-MM-DD."},
                "date_to": _DATE | {"description": "Hasta (incluida), AAAA-MM-DD."},
            }
        ),
        kind="read",
        skill="proyectos",
        groups=TIMESHEET_GROUPS,
    )
    def tool_my_timesheets(self, args):
        today = fields.Date.context_today(self)
        try:
            date_from = (
                date.fromisoformat(args["date_from"])
                if args.get("date_from")
                else today - timedelta(days=today.weekday())
            )
            date_to = (
                date.fromisoformat(args["date_to"]) if args.get("date_to") else today
            )
        except ValueError:
            raise XtdAiToolError(
                "validation", self.env._("Fecha en formato AAAA-MM-DD.")
            ) from None
        if date_from > date_to:
            raise XtdAiToolError(
                "validation", self.env._("La fecha inicial es posterior a la final.")
            )
        domain = [
            ("user_id", "=", self.env.uid),
            ("project_id", "!=", False),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        lines = self.env["account.analytic.line"].search(
            domain, order="date desc, id desc", limit=self._xtd_ai_limit(None)
        )
        total = self.env["account.analytic.line"]._read_group(
            domain, [], ["unit_amount:sum"]
        )[0][0]
        data = self._xtd_ai_list([self._xtd_ai_line_row(line) for line in lines])
        data.update(
            {
                "date_from": str(date_from),
                "date_to": str(date_to),
                "total_hours": round(total, 2),
            }
        )
        return {"data": data, "records": []}

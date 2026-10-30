from odoo import Command, api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiToolError

MAX_HOURS = 24.0


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["project.task"] = {
            "label": self.env._("tarea"),
            "skill": "proyectos",
            "create": True,
            "update": True,
            "create_class": "create_draft",
            "undo_create": True,
            # own tasks: the agent works on what is assigned to the user
            "domain": "_xtd_ai_domain_own_tasks",
            "defaults": "_xtd_ai_defaults_project_task",
            "check": "_xtd_ai_check_project_task",
            "chatter": True,
            "external": "_xtd_ai_external_project_task",
            "fields": {
                "name": {
                    "label": self.env._("Nombre"),
                    "risk": "low",
                    "required": True,
                },
                "project_id": {
                    "label": self.env._("Proyecto"),
                    "risk": "low",
                    "required": True,
                    # moving a task to another project changes its customer,
                    # its billing and who sees it
                    "update": False,
                },
                "description": {"label": self.env._("Descripción"), "risk": "low"},
                "date_deadline": {
                    "label": self.env._("Fecha límite"),
                    "risk": "low",
                },
                "priority": {"label": self.env._("Prioridad"), "risk": "low"},
                "tag_ids": {"label": self.env._("Etiquetas"), "risk": "low"},
                "allocated_hours": {
                    "label": self.env._("Horas previstas"),
                    "risk": "low",
                },
                "stage_id": {
                    "label": self.env._("Etapa"),
                    "risk": "low",
                    "create": False,
                    "domain_record": "_xtd_ai_domain_task_stage",
                },
                "user_ids": {"risk": "forbidden"},
                "partner_id": {"risk": "forbidden"},
                "active": {"risk": "forbidden"},
                "parent_id": {"risk": "forbidden"},
                "timesheet_ids": {"risk": "forbidden"},
                "sale_line_id": {"risk": "forbidden"},
            },
        }
        specs["account.analytic.line"] = {
            "label": self.env._("parte de horas"),
            "skill": "proyectos",
            "create": True,
            "update": True,
            "create_class": "create_draft",
            "undo_create": True,
            # own timesheets only (a project manager may see everyone's)
            "domain": "_xtd_ai_domain_own_timesheets",
            "check": "_xtd_ai_check_timesheet",
            "defaults": "_xtd_ai_defaults_timesheet",
            "fields": {
                "name": {
                    "label": self.env._("Descripción"),
                    "risk": "low",
                    "required": True,
                },
                "project_id": {"label": self.env._("Proyecto"), "risk": "low"},
                "task_id": {
                    "label": self.env._("Tarea"),
                    "risk": "low",
                    "domain": [("project_id", "!=", False)],
                },
                "date": {"label": self.env._("Fecha"), "risk": "low"},
                "unit_amount": {
                    "label": self.env._("Horas"),
                    "risk": "low",
                    "required": True,
                },
                # whose hours they are and what they cost: never the agent
                "employee_id": {"risk": "forbidden"},
                "user_id": {"risk": "forbidden"},
                "amount": {"risk": "forbidden"},
                "account_id": {"risk": "forbidden"},
                "partner_id": {"risk": "forbidden"},
                "so_line": {"risk": "forbidden"},
            },
        }
        return specs

    # -- tasks ---------------------------------------------------------------
    @api.model
    def _xtd_ai_domain_own_tasks(self, model):
        return [("user_ids", "in", self.env.uid), ("project_id", "!=", False)]

    @api.model
    def _xtd_ai_defaults_project_task(self, vals):
        # a task the agent creates is the user's own
        return {"user_ids": [Command.set(self.env.user.ids)]}

    @api.model
    def _xtd_ai_domain_task_stage(self, task):
        if task and task.project_id:
            return [("project_ids", "in", task.project_id.ids)]
        return []

    @api.model
    def _xtd_ai_check_project_task(self, task, vals):
        if vals.get("project_id"):
            project = self.env["project.project"].browse(vals["project_id"])
            project.check_access("read")
        hours = vals.get("allocated_hours")
        if hours is not None and hours > 10000:
            raise XtdAiToolError(
                "validation", self.env._("Horas previstas fuera de rango.")
            )

    @api.model
    def _xtd_ai_external_project_task(self, task):
        """Written by a portal user (project sharing) or arrived by email."""
        if task.create_uid.share:
            return True
        return any(
            message.message_type == "email"
            or (
                message.message_type == "comment"
                and message.author_id
                and not any(not user.share for user in message.author_id.user_ids)
            )
            for message in task.message_ids
        )

    # -- timesheets ----------------------------------------------------------
    @api.model
    def _xtd_ai_domain_own_timesheets(self, model):
        return [("user_id", "=", self.env.uid), ("project_id", "!=", False)]

    @api.model
    def _xtd_ai_check_timesheet(self, line, vals):
        hours = vals.get("unit_amount")
        if hours is not None and not 0 < hours <= MAX_HOURS:
            raise XtdAiToolError(
                "validation",
                self.env._("Las horas deben estar entre 0 y %s.", int(MAX_HOURS)),
            )
        if (
            not line
            and None not in vals.values()
            and not (vals.get("project_id") or vals.get("task_id"))
        ):
            raise XtdAiToolError(
                "validation",
                self.env._("Indica el proyecto o la tarea del parte de horas."),
            )
        task = self.env["project.task"].browse(vals.get("task_id") or [])
        project_id = vals.get("project_id") or (line and line.project_id.id)
        if task and project_id and task.project_id.id != project_id:
            raise XtdAiToolError(
                "validation",
                self.env._("La tarea «%s» es de otro proyecto.", task.name),
            )
        if not line and not self.env.user.employee_id:
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "Tu usuario no tiene empleado asociado: pide a RR. HH. que lo "
                    "vinculen para poder imputar horas."
                ),
            )

    @api.model
    def _xtd_ai_defaults_timesheet(self, vals):
        defaults = {}
        if vals.get("task_id") and not vals.get("project_id"):
            task = self.env["project.task"].browse(vals["task_id"])
            defaults["project_id"] = task.project_id.id
        return defaults

from odoo import _, api, fields, models


class ProjectTaskKind(models.Model):
    _name = "project.task.kind"

    project_task_id = fields.One2many(
        comodel_name="project.task",
        inverse_name="project_task_kind_id",
    )
    name = fields.Char(
        required=True,
    )
    task_count = fields.Integer(
        "Number of task",
        compute="_compute_task_count",
    )

    def action_view_task(self):
        self.ensure_one()
        task_ids = self._get_task().ids
        action = {
            "res_model": "project.task",
            "type": "ir.actions.act_window",
        }
        if len(task_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": task_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("Task from hind %s", self.name),
                    "domain": [("id", "in", task_ids)],
                    "view_mode": "tree,form",
                }
            )
        return action

    def _compute_task_count(self):
        for order in self:
            order.task_count = len(self._get_task())

    def _get_task(self):
        return self.env["project.task"].search([("project_task_kind_id", "=", (self.id))])

class ProjectTask(models.Model):
    _inherit = "project.task"

    project_task_kind_id = fields.Many2one(
        comodel_name="project.task.kind",
    )

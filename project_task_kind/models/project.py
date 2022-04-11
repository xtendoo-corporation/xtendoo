from odoo import api, fields, models


class ProjectTaskKind(models.Model):
    _name = "project.task.kind"

    project_task_id = fields.One2many(
        comodel_name="project.task",
        inverse_name="project_task_kind_id",
    )
    name = fields.Char(
        required=True,
    )


class ProjectTask(models.Model):
    _inherit = "project.task"

    project_task_kind_id = fields.Many2one(
        comodel_name="project.task.kind",
    )

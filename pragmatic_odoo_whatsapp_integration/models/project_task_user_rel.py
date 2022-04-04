
from odoo import api, fields, models, _, tools


class project_task_user_rel(models.Model):
    _inherit = 'project.task.stage.personal'
    _description = 'Project Task User Rel'

    whatsapp_msg_id = fields.Char(string='Whatsapp Message id')


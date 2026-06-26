# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Integración con FSM
    fsm_order_id = fields.Many2one(
        'fsm.order',
        string='Orden de Servicio FSM',
        help="Orden de servicio de campo relacionada"
    )
    is_fsm_task = fields.Boolean(
        string='Es Tarea FSM',
        related='project_id.is_fsm',
        store=True
    )

    def action_view_fsm_order(self):
        """Ver la orden FSM relacionada"""
        if self.fsm_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'fsm.order',
                'res_id': self.fsm_order_id.id,
                'view_mode': 'form',
            }


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_fsm = fields.Boolean(
        string='Proyecto FSM',
        help="Este proyecto se usa para gestión de servicios de campo"
    )
    # Comentado temporalmente hasta implementar el modelo fsm.team
    # fsm_team_id = fields.Many2one(
    #     'fsm.team',
    #     string='Equipo FSM',
    #     help="Equipo de servicio de campo asignado a este proyecto"
    # )

# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # Integración con FSM
    fsm_order_id = fields.Many2one(
        'fsm.order',
        string='Orden de Servicio FSM',
        help="Orden de servicio de campo relacionada"
    )
    is_fsm_timesheet = fields.Boolean(
        string='Es Timesheet FSM',
        compute='_compute_is_fsm_timesheet',
        store=True
    )

    @api.depends('fsm_order_id')
    def _compute_is_fsm_timesheet(self):
        for line in self:
            line.is_fsm_timesheet = bool(line.fsm_order_id)

    def action_view_fsm_order(self):
        """Ver la orden FSM relacionada"""
        if self.fsm_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'fsm.order',
                'res_id': self.fsm_order_id.id,
                'view_mode': 'form',
            }

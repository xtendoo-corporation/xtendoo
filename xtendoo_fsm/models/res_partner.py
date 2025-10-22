# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'


    # Relaciones FSM
    fsm_order_ids = fields.One2many(
        'fsm.order',
        'partner_id',
        string='Órdenes de Trabajo'
    )

    # Estadísticas FSM
    fsm_order_count = fields.Integer(
        string='Total Órdenes de Trabajo',
        compute='_compute_fsm_statistics'
    )

    @api.depends('fsm_order_ids')
    def _compute_fsm_statistics(self):
        for partner in self:
            partner.fsm_order_count = len(partner.fsm_order_ids)

    def action_view_fsm_orders(self):
        """Ver órdenes de trabajo del cliente"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Órdenes de Trabajo - {self.name}',
            'res_model': 'fsm.order',
            'view_mode': 'tree,form,kanban',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }

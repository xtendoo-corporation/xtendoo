# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Integración con FSM
    fsm_order_id = fields.Many2one(
        'daruclima.fsm.order',
        string='Orden de Servicio FSM',
        help="Orden de servicio de campo relacionada"
    )

    def action_view_fsm_order(self):
        """Ver la orden FSM relacionada"""
        if self.fsm_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'daruclima.fsm.order',
                'res_id': self.fsm_order_id.id,
                'view_mode': 'form',
            }


class StockMove(models.Model):
    _inherit = 'stock.move'

    fsm_order_id = fields.Many2one(
        'daruclima.fsm.order',
        string='Orden de Servicio FSM',
        related='picking_id.fsm_order_id',
        store=True
    )

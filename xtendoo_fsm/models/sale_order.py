# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_order_id = fields.Many2one(
        'fsm.order',
        string='Orden de Trabajo FSM',
        help="Orden de trabajo FSM que originó esta orden de venta"
    )
    aseguradora_id = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        help='Aseguradora asociada a la orden de trabajo FSM'
    )
    importe_franquicia = fields.Float(
        string='Importe Franquicia',
        help='Importe de la franquicia de la orden de trabajo FSM'
    )

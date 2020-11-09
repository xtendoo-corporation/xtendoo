# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    move_product_qty = fields.Float(
        compute='_compute_picking_waiting_product_qty',
        string='Pickings'
    )

    def _compute_picking_waiting_product_qty(self):
        pick_lines = self.env['stock.move.line'].search([('picking_id', '=', self.id)])
        total_quantity=0
        for line in pick_lines:
            pick_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')])
            delivery_lines = self.env['stock.move'].search([('product_id', '=', line.product_id.id), ('picking_type_id','=',pick_type[0].id)])
            for delivery_line in delivery_lines:
                total_quantity= total_quantity + delivery_line.product_uom_qty
        self.move_product_qty=float_round(total_quantity,
                                                   precision_rounding=pick_lines[0].product_id.uom_id.rounding)



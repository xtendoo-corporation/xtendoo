# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    @api.depends('product_type', 'product_uom_qty', 'qty_delivered', 'state', 'move_ids', 'product_uom')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state in ('draft', 'sent', 'sale') and line.product_type == 'product' and line.product_uom and line.qty_to_deliver > 0:
                if line.state == 'sale' and not line.move_ids:
                    line.display_qty_widget = False
                else:
                    line.display_qty_widget = True
                    #calculamos si esta totalmente entregado, para mostrar o no el widget
                    qty_total = 0.00
                    for move in line.move_ids:
                        if move.state == 'done':
                            qty_total += move.product_uom_qty
                    if qty_total == line.product_uom_qty:
                            line.display_qty_widget = False
            else:
                line.display_qty_widget = False

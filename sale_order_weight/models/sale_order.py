# Copyright 2021 Manuel Calero Solis (http://www.xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_weight = fields.Float(compute='_compute_total_weight', string='Total Weight', store=True)

    @api.depends('order_line.weight')
    def _compute_total_weight(self):
        for order in self:
            total_weight = 0.0
            for line in order.order_line:
                total_weight += line.weight
            order.total_weight = total_weight


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    weight = fields.Float(compute='_compute_weight', string='Weight', store=True)

    @api.depends('product_uom_qty', 'product_id.weight')
    def _compute_weight(self):
        for line in self:
            line.weight += line.product_id.weight * line.product_uom_qty

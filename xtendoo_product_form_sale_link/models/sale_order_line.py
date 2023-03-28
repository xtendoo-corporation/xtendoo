# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    date_order = fields.Datetime(
        related="order_id.date_order",
        string="Order Date",
        store=True,
        readonly=True,
    )
    qty_pending = fields.Float(
        string="Pending quantity",
        compute='_compute_qty_pending',
        store=True,
    )

    @api.depends('product_uom_qty', 'qty_delivered')
    def _compute_qty_pending(self):
        for line in self:
            line.qty_pending = line.product_uom_qty - line.qty_delivered


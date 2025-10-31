# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin_percent_show = fields.Float(
        compute="_compute_margin_percent",
        digits=(16, 6),
        store=True,
    )

    @api.depends("margin")
    def _compute_margin_percent(self):
        for line in self:
            line.margin_percent_show = line.price_subtotal and line.margin / line.price_subtotal


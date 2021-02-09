# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin_percent = fields.Float(
        compute="_compute_margin_percent",
        digits=(16, 2),
        store=True,
    )

    @api.depends("margin")
    def _compute_margin_percent(self):
        for line in self:
            line.margin_percent = (
                line.price_subtotal and line.margin / line.price_subtotal * 100 or 0.0
            )

# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_address_display = fields.Char(
        string="Shipping Address",
        compute="_compute_shipping_address_display",
        store=True,
        readonly=True,
    )

    @api.depends("partner_shipping_id", "partner_shipping_id.name", "partner_shipping_id.display_name")
    def _compute_shipping_address_display(self):
        """Compute shipping address display for tree view."""
        for order in self:
            if order.partner_shipping_id:
                order.shipping_address_display = order.partner_shipping_id.display_name
            else:
                order.shipping_address_display = ""



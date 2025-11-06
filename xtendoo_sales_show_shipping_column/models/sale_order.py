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

    @api.depends("partner_shipping_id", "partner_shipping_id.name",
                 "partner_shipping_id.street", "partner_shipping_id.city",
                 "partner_shipping_id.zip", "partner_shipping_id.state_id",
                 "partner_shipping_id.country_id")
    def _compute_shipping_address_display(self):
        """Compute shipping address display for tree view."""
        for order in self:
            if order.partner_shipping_id:
                partner = order.partner_shipping_id
                address_parts = []

                if partner.name:
                    address_parts.append(partner.name)
                if partner.street:
                    address_parts.append(partner.street)
                if partner.zip or partner.city:
                    city_zip = []
                    if partner.zip:
                        city_zip.append(partner.zip)
                    if partner.city:
                        city_zip.append(partner.city)
                    address_parts.append(" ".join(city_zip))
                if partner.state_id:
                    address_parts.append(partner.state_id.name)
                if partner.country_id:
                    address_parts.append(partner.country_id.name)

                order.shipping_address_display = ", ".join(address_parts)
            else:
                order.shipping_address_display = False


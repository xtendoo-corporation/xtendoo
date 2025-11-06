# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    shipping_address_display = fields.Char(
        string="Shipping Address",
        compute="_compute_shipping_address_display",
        store=True,
        readonly=True,
    )

    @api.depends("partner_shipping_id", "partner_shipping_id.name")
    def _compute_shipping_address_display(self):
        """Compute shipping address display for tree view."""
        for move in self:
            if move.partner_shipping_id:
                move.shipping_address_display = move.partner_shipping_id
            else:
                move.shipping_address_display = False


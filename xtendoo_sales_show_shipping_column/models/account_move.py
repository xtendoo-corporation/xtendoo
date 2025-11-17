# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    partner_shipping_id = fields.Many2one(
        comodel_name="res.partner",
        string="Delivery Address",
        compute="_compute_partner_shipping_id",
        store=True,
        readonly=False,
    )

    shipping_address_display = fields.Char(
        string="Shipping Address",
        compute="_compute_shipping_address_display",
        store=True,
        readonly=True,
    )

    @api.depends("invoice_line_ids.sale_line_ids.order_id.partner_shipping_id")
    def _compute_partner_shipping_id(self):
        """Get shipping address from related sale order."""
        for move in self:
            if move.move_type in ("out_invoice", "out_refund"):
                sale_orders = move.invoice_line_ids.sale_line_ids.order_id
                if sale_orders:
                    move.partner_shipping_id = sale_orders[0].partner_shipping_id
                elif not move.partner_shipping_id:
                    move.partner_shipping_id = False
            else:
                move.partner_shipping_id = False

    @api.depends("partner_shipping_id", "partner_shipping_id.name")
    def _compute_shipping_address_display(self):
        """Compute shipping address display for tree view."""
        for move in self:
            if move.partner_shipping_id:
                move.shipping_address_display = move.partner_shipping_id.name
            else:
                move.shipping_address_display = ""


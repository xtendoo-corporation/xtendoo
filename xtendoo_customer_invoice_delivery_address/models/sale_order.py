# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.onchange("partner_id")
    def onchange_partner_id(self):
        super().onchange_partner_id()

        domain = {}
        for self in self:
            if self.partner_id:
                invoice_address = self.env["res.partner"].search(
                    [("parent_id", "=", self.partner_id.id), ("type", "=", "invoice"),],
                    limit=1,
                )
                delivery_address = self.env["res.partner"].search(
                    [
                        ("parent_id", "=", self.partner_id.id),
                        ("type", "=", "delivery"),
                    ],
                    limit=1,
                )
                if len(invoice_address) == 0:
                    domain["partner_invoice_id"] = [
                        ("id", "=", self.partner_id.id),
                    ]
                else:
                    self.partner_invoice_id = invoice_address
                    domain["partner_invoice_id"] = [
                        ("type", "=", "invoice"),
                        ("id", "child_of", self.partner_id.id),
                    ]
                if len(delivery_address) == 0:
                    domain["partner_shipping_id"] = [
                        ("id", "=", self.partner_id.id),
                    ]
                else:
                    self.partner_shipping_id = delivery_address
                    domain["partner_shipping_id"] = [
                        ("type", "=", "delivery"),
                        ("id", "child_of", self.partner_id.id),
                    ]
        return {"domain": domain}

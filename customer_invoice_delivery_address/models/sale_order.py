# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.onchange("partner_id")
    def onchange_partner_id(self):
        super().onchange_partner_id()
        domain = {}
        for record in self:
            if record.partner_id:
                domain["partner_invoice_id"] = [
                    ("type", "=", "invoice"),
                    ("id", "child_of", record.partner_id.id),
                ]
                domain["partner_shipping_id"] = [
                    ("type", "=", "delivery"),
                    ("id", "child_of", record.partner_id.id),
                ]
        return {"domain": domain}

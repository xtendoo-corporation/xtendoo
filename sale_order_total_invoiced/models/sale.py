# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        readonly=True,
        compute="_compute_total_invoiced",
        help="Sale order total invoiced",
    )

    def _compute_total_invoiced(self):
        for record in self:
            total_invoice = 0.0
            for invoice in record.invoice_ids:
                total_invoice += invoice.amount_total_signed
            record.total_invoiced = total_invoice



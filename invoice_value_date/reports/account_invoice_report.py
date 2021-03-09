# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    date_value = fields.Date(
        readonly=True,
        string="Value Date",
    )

    def _select(self):
        return super()._select() + ", sub.date_value as date_value"

    def _sub_select(self):
        return super()._sub_select() + ", ai.date_value as date_value"

    def _group_by(self):
        return super()._group_by() + ", ai.date_value"

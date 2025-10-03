# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models
from odoo.osv.expression import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    date_value = fields.Date(
        readonly=True,
        string="Value Date",
    )

    def _select(self):
        return SQL("%s, date_value as date_value", super()._select())

    def _sub_select(self):
        return SQL("%s, date_value as date_value", super()._sub_select())

    def _group_by(self):
        return super()._group_by() + ", date_value"

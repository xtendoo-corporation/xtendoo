# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    date_value = fields.Date(readonly=True, string="Value Date")

    _depends = {
        'account.move': ['date_value'],
    }

    def _select(self):
        return super()._select() + ", move.date_value"

    def _group_by(self):
        return super()._group_by() + ", move.date_value"

# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    date_value = fields.Date(
        string='Date Value',
        help="Keep empty to use the current date",
        copy=False,
        default=_get_default_date,
    )

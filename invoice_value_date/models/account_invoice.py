from odoo import models, fields, api, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    date_value = fields.Date(
        string='Value Date',
        help="Keep empty to use the current date",
        copy=False,
    )

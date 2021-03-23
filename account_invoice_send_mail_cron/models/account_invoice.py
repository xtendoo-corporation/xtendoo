# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceSendMailCron(models.Model):
    _name = "account.invoice.send.mail"
    _description = "Account Invoice Send Mail Cron"

    def _cron_send_account_invoice_email(self):
        invoices = self.env['account.move'].search([
            ('invoice_sent', '=', False),
            ('type', '=', 'out_invoice'),
        ])
        print("invoices ::::", invoices)
        raise ValidationError('Cron is running::::')

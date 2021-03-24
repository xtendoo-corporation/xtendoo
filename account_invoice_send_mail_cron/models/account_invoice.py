# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _


class AccountInvoiceSendMailCron(models.Model):
    _name = "account.invoice.send.mail"
    _description = "Account Invoice Send Mail Cron"

    @api.model
    def _cron_send_account_invoice_email(self):
        invoices = self.env['account.move'].search([
            # ('invoice_sent', '=', False),
            ('type', '=', 'out_invoice'),
            ('partner_id.email', '!=', False),
            ('id', '=', 12905),
        ])
        for invoice in invoices:
            print("invoice num. ::::", invoice.name)
            print("invoice sent ::::", invoice.invoice_sent)
            print("invoice mail ::::", invoice.partner_id.email)
            invoice._send_email()




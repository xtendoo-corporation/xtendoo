

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    #validate and send by mail
    def validate_and_send_by_mail(self):
        self.action_post()
        if self.partner_id.email:
            return self.action_invoice_sent()



# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.model
    def default_get(self, default_fields):
        if self.env.user.create_direct_invoice:
            return super(AccountInvoice, self).default_get(default_fields)

        raise ValidationError(_("You are not allowed to create invoices."))

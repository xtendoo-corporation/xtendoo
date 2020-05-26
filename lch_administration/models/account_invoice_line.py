# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoice(models.Model):
    _inherit = 'account.invoice.line'
    _name = 'account.invoice.line'

    is_admin = fields.Boolean(
        comodel_name='account.invoice.line',
        compute='_is_admin',
        string="isAdmin"
    )
    @api.one
    def _is_admin(self):
        self.is_admin=self.env.user.administration
        logging.info('isAdmin')
        if not self.env.user.administration:
            self.is_admin=True
        if self.env.user.administration:
            logging.info('ES TRUE')
            return
        logging.info('ES FALSE')

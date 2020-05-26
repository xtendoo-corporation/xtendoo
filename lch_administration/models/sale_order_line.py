# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoice(models.Model):
    _inherit = 'sale.order.line'
    _name = 'sale.order.line'

    is_admin = fields.Boolean(
        comodel_name='sale.order.line',
        compute='_is_admin',
        string="isAdmin"
    )
    @api.one
    def _is_admin(self):
        self.is_admin=self.env.user.administration
        logging.info('isAdmin')
        if self.env.user.administration:
            logging.info('ES TRUE')
            return
        logging.info('ES FALSE')

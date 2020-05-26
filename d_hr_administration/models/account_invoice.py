# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.model
    def default_get(self, default_fields):
        """Si el contexto trae el dato 'active_model' y ese model es 'sale_order' eso quiere decir
        que viene de un pedido por tanto lo dejamos pasar
        """
        #logging.info('get')
        #logging.info(self.env.context.get('active_model', ''))
        #logging.info(self.env.context.get('is_sale', ''))
        if self.env.context.get('active_model', '') == 'sale.order' or self.env.user.administration or self.env.context.get('is_sale', '') == True:
            return super(AccountInvoice, self).default_get(default_fields)

        raise ValidationError(("You are not allowed to create invoices."))

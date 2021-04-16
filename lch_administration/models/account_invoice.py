# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoice(models.Model):
    _inherit = ["account.invoice", "administrator.mixin.rule"]
    _name = 'account.invoice'


    @api.model
    def default_get(self, default_fields):
        """Si el contexto trae el dato 'active_model' y ese model es 'sale_order' eso quiere decir
        que viene de un pedido por tanto lo dejamos pasar
        """
        if not self.env["res.users"].has_group("lch_administration.administration_group"):
            active_model=""
            logging.info('********************************************')
            logging.info(self._context)
            if self._context.get('params'):
                if self._context.get('params').get('model'):
                    active_model=self._context.get('params').get('model')
            if self._context.get('search_default_my_quotation'):
                active_model="sale.order"
            if self._context.get('active_model'):
                active_model=self._context.get('active_model')
            if active_model != "sale.order":
                raise ValidationError(("No tiene permisos para crear facturas directas"))
        return super(AccountInvoice, self).default_get(default_fields)

    @api.multi
    def action_invoice_cancel(self):
        if not self.env.user.administration:
            raise ValidationError(("No tiene permisos para cancelar facturas"))
        return self.filtered(lambda inv: inv.state != 'cancel').action_cancel()

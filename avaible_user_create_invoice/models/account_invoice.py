# -- coding: utf-8 --
from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.model
    def default_get(self, default_fields):
        """Si el contexto trae el dato 'active_model' y ese model es 'sale_order' eso quiere decir
        que viene de un pedido por tanto lo dejamos pasar
        """

        if self.env.context.get('active_model', '') == 'sale.order' or self.env.user.create_direct_invoice:
            return super(AccountInvoice, self).default_get(default_fields)

        raise ValidationError(_("You are not allowed to create invoices."))

# Copyright 2021 Daniel Domínguez - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from itertools import groupby
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False):
        #return super(SaleOrder, self)._create_invoices(self,grouped=False, final=False)
        for order in self:
            if order.partner_id.monthly_invoicing:
                date_order=order.date_order
                date_today=datetime.now()
                if format(date_order.month) == format(date_today.month):
                    raise ValidationError(("El cliente %s factura mensualmente, el pedido %s tiene fecha del mes en curso") %(order.partner_id.name,order.name))
        for order in self:
            return super(SaleOrder, self)._create_invoices(self)
        


    #@api.model
    #def default_get(self, default_fields):
        #print("*"*20)
        #print(self._context)
        #if self._context.get('default_type') == 'out_invoice':
            #return super(AccountMove, self).default_get(default_fields)
        #raise ValidationError(("No tiene permisos para crear facturas"))
        #return super(AccountInvoice, self).default_get(default_fields)
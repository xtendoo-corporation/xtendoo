# Copyright 2021 Daniel Domínguez - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False):
        for order in self:
            if order.partner_id.monthly_invoicing:
                date_order = format(order.date_order.month) + format(order.date_order.year)
                date_today = format(datetime.now().month) + format(datetime.now().year)
                if date_order == date_today:
                    raise ValidationError(
                        ("El cliente %s factura mensualmente, el pedido %s tiene fecha del mes en curso")
                        %
                        (order.partner_id.name, order.name)
                    )
        return super(SaleOrder, self)._create_invoices(grouped, final)

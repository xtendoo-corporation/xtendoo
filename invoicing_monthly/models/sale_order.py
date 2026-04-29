# Copyright 2021 Daniel Domínguez - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False, date=None):
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
        return super()._create_invoices(grouped=grouped, final=final, date=date)

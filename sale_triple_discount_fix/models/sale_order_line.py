#Copyright 2019 Xtendoo -DDL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

import logging

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.one
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','discount2','discount3')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            # to avoid coupling these calculations must be passed to a method
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            price *= (1 - (self.discount2 or 0.0) / 100.0)
            price *= (1 - (self.discount3 or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

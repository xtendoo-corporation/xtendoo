
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from lxml import etree

import logging


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_dpp = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento PP',
    )

    client_discount = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento Cliente',
    )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super().onchange_partner_id()
        self.discount_dpp = self.partner_id.discount_dpp
        self.client_discount = self.partner_id.client_discount
        self.onchange_client_discount_line()

    @api.onchange('discount_dpp')
    def onchange_general_discount(self):

        logging.info("*"*80)
        logging.info(self.discount_dpp)

        self.mapped('order_line').update({
            'discount3': self.discount_dpp,
        })
        raise ValidationError("discount_dpp change")        

    @api.onchange('client_discount')
    def onchange_client_discount(self):
        
        logging.info("*"*80)
        logging.info(self.client_discount)

        self.mapped('order_line').update({
            'discount2': self.client_discount,
        })
        raise ValidationError("client_discount change")        

    @api.onchange('order_line')
    def onchange_client_discount_line(self):
        self.mapped('order_line').update({
            'discount3': self.discount_dpp,
            'discount2': self.client_discount,
        })

    def _get_delivery_carrier_products(self):
        self.env["delivery.carrier"].mapped("product_id")

    @api.multi
    def _action_confirm(self):
        delivery_products = self._get_delivery_carrier_products()

        logging.info(delivery_products)

        for order_line in self.mapped('order_line'):

            if (order_line.product_id.default_code == 'ENT30' or order_line.product_id.default_code == 'ENT0'):
                order_line.update({
                    'discount3': '0.00',
                })

                order_line.update({
                    'discount2': '0.00',
                })

            if( order_line.product_id.default_code !='ENT30' and order_line.product_id.default_code != 'ENT0'):

                if(order_line.discount2 != self.partner_id.client_discount and order_line.discount2 != 0.00):

                    order_line.update({
                        'discount3': self.discount_dpp,
                    })

                    order_line.update({
                        'discount2': self.client_discount,
                    })

        super().onchange_partner_id()

        return True


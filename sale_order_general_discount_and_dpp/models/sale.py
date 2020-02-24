
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
        super(SaleOrder, self).onchange_partner_id()
        self.discount_dpp = self.partner_id.discount_dpp
        self.client_discount = self.partner_id.client_discount
        self.onchange_client_discount_line()

    @api.onchange('discount_dpp')
    def onchange_general_discount(self):

        for order_line in self.order_line:
            logging.info("*"*80)
            logging.info(order_line.product_id)
            logging.info(order_line.product_id.id)
            logging.info(order_line.product_id.name)

            if self._is_a_delivery_product(order_line.product_id):
                logging.info("lo pongo a cero >>>>>>>>>>>>>>>>")
                logging.info(order_line.product_id.name)
                order_line.update({
                    'discount3': '0.00',
                })
            else:
                logging.info("pongo su valor <<<<<<<<<<<<<<<<<<<<<<")
                logging.info(order_line.product_id.name)
                logging.info(self.discount_dpp)
                order_line.update({
                    'discount3': self.discount_dpp,
                })
        # raise ValidationError("discount_dpp change")        

    def _is_a_delivery_product(self, product_id):
        for product in (self.env["delivery.carrier"].search([('id', '!=', 0)])):
            logging.info("search###################################")
            logging.info(product.product_id)
            if product.product_id == product_id:
                return True
        return False

    @api.onchange('client_discount')
    def onchange_client_discount(self):
        for order_line in self.order_line:
            if self._is_a_delivery_product(order_line.product_id):
                order_line.update({
                    'discount2': '0.00',
                })
            else:
                order_line.update({
                    'discount2': self.client_discount,
                })

    @api.onchange('order_line')
    def onchange_client_discount_line(self):
        self.mapped('order_line').update({
            'discount2': self.client_discount,
            'discount3': self.discount_dpp,
        })

    def _get_delivery_carrier_products(self):
        return self.env["delivery.carrier"].mapped("product_id")

    @api.multi
    def _action_confirm(self):
        delivery_products = self._get_delivery_carrier_products()

        logging.info(delivery_products)

        for order_line in self.mapped('order_line'):
            if (order_line.product_id.default_code in delivery_products):
                order_line.update({
                    'discount3': '0.00',
                    'discount2': '0.00',
                })

        super().onchange_partner_id()

        return True


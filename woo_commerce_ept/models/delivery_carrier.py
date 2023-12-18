# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    """
    Inherited to add the woocommerce carriers.
    @author: Meera Sidapara on Date 18-04-2022.
    """
    _inherit = "delivery.carrier"

    woo_code = fields.Char(help="WooCommerce Delivery Code", compute='_set_woocommerce_shipping_code', store=True)
    woo_shipping_method_id = fields.Many2one('woo.shipping.method', help="WooCommerce Shipping Methods")

    @api.depends('woo_shipping_method_id')
    def _set_woocommerce_shipping_code(self):
        """
        This method is used to set WooCommerce code base on WooCommerce shipping methods.
        @author: Meera Sidapara on Date 18-04-2022.
        """
        self.write({'woo_code': self.woo_shipping_method_id.code})

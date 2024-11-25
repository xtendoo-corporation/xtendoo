# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError


class WooShippingMethod(models.Model):
    _name = "woo.shipping.method"
    _description = "WooCommerce Shipping Method"

    name = fields.Char("Shipping Method", required=True)
    code = fields.Char("Shipping Code", required=True,
                       help="The shipping code should match Shipping ID in your WooCommerce Checkout Settings.")
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instance", required=True)

    _sql_constraints = [('_shipping_method_unique_constraint', 'unique(code,woo_instance_id)',
                         "Shipping method code must be unique in the list")]

    def woo_check_and_create_shipping_methods(self, instance, shipping_methods_data):
        """
        This method checks for existing methods and creates if not existed.
        @param instance: Record of Instance.
        @param shipping_methods_data: Response from WooCommerce of shipping methods.
        """
        for shipping_method in shipping_methods_data:
            name = shipping_method.get('title')
            code = shipping_method.get('id')
            existing_shipping_method = self.search([('code', '=', code), ('woo_instance_id', '=', instance.id)]).ids
            if existing_shipping_method or not name or not code:
                continue
            self.create({'name': name, 'code': code, 'woo_instance_id': instance.id})
        return True

    def woo_get_shipping_method(self, instance):
        """
        Get all shipping methods from woocommerce by calling API.
        """
        log_line_obj = self.env["common.log.lines.ept"]
        wc_api = instance.woo_connect()
        try:
            response = wc_api.get("shipping_methods")
        except Exception as error:
            raise UserError(_("Something went wrong while importing Shipping Methods.\n\nPlease Check your Connection "
                              "and Instance Configuration.\n\n" + str(error)))
        if response.status_code not in [200, 201]:
            message = response.content
            if message:
                log_line_obj.create(type="import", module="woocommerce_ept", woo_instance_id=instance.id,
                                    model_name=self._name, message=message)
                return False
        shipping_data = response.json()
        self.woo_check_and_create_shipping_methods(instance, shipping_data)

        return True

# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError


class WooPaymentGateway(models.Model):
    _name = "woo.payment.gateway"
    _description = "WooCommerce Payment Gateway"

    name = fields.Char("Payment Method", required=True)
    code = fields.Char("Payment Code", required=True,
                       help="The payment code should match Gateway ID in your WooCommerce Checkout Settings.")
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instance", required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('_payment_gateway_unique_constraint', 'unique(code,woo_instance_id)',
                         "Payment gateway code must be unique in the list")]

    def woo_check_and_create_payment_methods(self, instance, payment_methods_data):
        """
        This method checks for existing methods and creates if not existed.
        @param instance: Record of Instance.
        @param payment_methods_data: Response from WooCommerce of payment methods.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for payment_method in payment_methods_data:
            if payment_method.get('enabled'):
                name = payment_method.get('title')
                code = payment_method.get('id')
                existing_payment_gateway = self.search([('code', '=', code), ('woo_instance_id', '=', instance.id)]).ids
                if existing_payment_gateway or not name or not code:
                    continue
                self.create({'name': name, 'code': code, 'woo_instance_id': instance.id})
        return True

    def woo_get_payment_gateway(self, instance):
        """
        Get all active payment methods from woocommerce by calling API.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        log_line_obj = self.env["common.log.lines.ept"]
        wc_api = instance.woo_connect()
        try:
            response = wc_api.get("payment_gateways")
        except Exception as error:
            raise UserError(_("Something went wrong while importing Payment Gateways.\n\nPlease Check your Connection "
                              "and Instance Configuration.\n\n" + str(error)))
        if response.status_code not in [200, 201]:
            message = response.content
            if message:
                log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                        woo_instance_id=instance.id, model_name=self._name,
                                                        message=message)
                return False
        payment_data = response.json()
        self.woo_check_and_create_payment_methods(instance, payment_data)

        return True

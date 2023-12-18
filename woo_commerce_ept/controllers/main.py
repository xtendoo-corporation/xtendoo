# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Controller for Webhook.
"""
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger("WooCommerce")


class Webhook(http.Controller):
    """
    Controller for Webhooks.
    @author: Maulik Barad on Date 09-Jan-2019.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """

    @http.route("/update_product_webhook_odoo", csrf=False, auth="public", type="json")
    def update_product_webhook(self):
        """
        Route for handling the product update webhook of WooCommerce.
        This method will only process main products, not variations.
        @author: Haresh Mori on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        _logger.info("UPDATE PRODUCT WEBHOOK call for this product: %s", request.get_json_data().get("name"))
        self.product_webhook_process()
        return

    @http.route("/delete_product_webhook_odoo", csrf=False, auth="public", type="json")
    def delete_product_webhook(self):
        """
        Route for handling the product delete webhook for WooCommerce
        This method will only process main products, not variations.
        @author: Haresh Mori on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        _logger.info("DELETE PRODUCT WEBHOOK call for this product: %s", request.get_json_data())
        res, instance = self.get_basic_info()
        if not res:
            return

        woo_template = request.env["woo.product.template.ept"].sudo().search([("woo_tmpl_id", "=", res.get('id')),
                                                                              ("woo_instance_id", "=", instance.id)],
                                                                             limit=1)
        if woo_template:
            woo_template.write({'active': False})
        return

    @http.route("/restore_product_webhook_odoo", csrf=False, auth="public", type="json")
    def restore_product_webhook(self):
        """
        Route for handling the product restore webhook of WooCommerce.
        This method will only process main products, not variations.
        @author: Haresh Mori on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        _logger.info("RESTORE PRODUCT WEBHOOK call for this product: %s", request.get_json_data().get("name"))
        res, instance = self.get_basic_info()
        if not res:
            return
        woo_template = request.env["woo.product.template.ept"].with_context(active_test=False).search(
            [("woo_tmpl_id", "=", res.get('id')), ("woo_instance_id", "=", instance.id)], limit=1)
        if woo_template:
            woo_template.write({'active': True})
            woo_template._cr.commit()
        self.product_webhook_process()
        return

    def product_webhook_process(self):
        """
        This method used to process the product webhook response.
        @author: Haresh Mori on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return
        wc_api = instance.woo_connect()

        woo_template = request.env["woo.product.template.ept"].with_context(active_test=False).search(
            [("woo_tmpl_id", "=", res.get('id')),
             ("woo_instance_id", "=", instance.id)], limit=1)

        if woo_template or (res.get("status") == "publish" and res.get("type") != "variation"):
            request.env["woo.product.data.queue.ept"].sudo().create_product_queue_from_webhook(res, instance, wc_api)
        return

    @http.route(["/update_order_webhook_odoo", "/delete_order_webhook_odoo"], csrf=False, auth="public", type="json")
    def update_order_webhook(self):
        """
        Route for handling the order modification webhook of WooCommerce.
        @author: Maulik Barad on Date 21-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return
        delete_webhook = bool(request.httprequest.path.split('/')[1] == "delete_order_webhook_odoo")
        _logger.info('Order webhook call for Woo order : %s', res.get('id'))
        if instance.active:
            sale_order_obj = request.env["sale.order"]
            domain = [("woo_instance_id", "=", instance.id), ("woo_order_id", "=", res.get("id"))]
            if delete_webhook:
                res.update({"number": res.get("id"), "status": "cancelled"})
            else:
                domain.append(("woo_order_number", "=", res.get("number")))

            order = sale_order_obj.sudo().search(domain)
            if order:
                sale_order_obj.sudo().process_order_via_webhook(res, instance, True)
                if delete_webhook:
                    _logger.info("Cancelled order %s of %s via Webhook as deleted in Woo Successfully", order.name,
                                 instance.name)

            elif res.get("status") in instance.import_order_status_ids.mapped("status") + ['completed']:
                sale_order_obj.sudo().process_order_via_webhook(res, instance)

        return

    @http.route("/check_webhook", csrf=False, auth="public", type="json")
    def check_webhook(self):
        """
        Route for handling the order modification webhook of WooCommerce.
        @author: Maulik Barad on Date 21-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res = request.get_json_data()
        headers = request.httprequest.headers
        event = headers.get("X-Wc-Webhook-Event")
        _logger.warning("Record %s %s - %s via Webhook", res.get("id"), event,
                        res.get("name", res.get("code", "")) if event != "deleted" else "Done")
        # _logger.warning(res)

    @http.route("/update_customer_webhook_odoo", csrf=False, auth="public", type="json")
    def update_customer_webhook(self):
        """
        Route for handling the customer update webhook of WooCommerce.
        @author: Dipak Gogiya on Date 01-Jan-2020
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return
        _logger.info("UPDATE CUSTOMER WEBHOOK call for Customer: %s",
                     res.get("first_name") + " " + res.get("last_name"))

        if res.get('role') != 'customer':
            _logger.info("Type is not 'customer' for this customer: %s. The type is '%s'.",
                         res.get("first_name") + " " + res.get("last_name"), res.get('role'))
            return

        customer_data_queue_obj = request.env["woo.customer.data.queue.ept"]
        customer_data_queue_obj.sudo().create_customer_data_queue_for_webhook(instance, res)
        return

    @http.route("/delete_customer_webhook_odoo", csrf=False, auth="public", type="json")
    def delete_customer_webhook(self):
        """
        Route for handling the customer deletion webhook of WooCommerce.
        @author: Dipak Gogiya on Date 31-Dec-2019
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return
        _logger.info("DELETE CUSTOMER WEBHOOK call for this Customer: %s", res)
        woo_partner = request.env['woo.res.partner.ept'].sudo().search([('woo_customer_id', '=', res.get('id')),
                                                                        ('woo_instance_id', '=', instance.id)])
        if woo_partner:
            woo_partner.partner_id.is_woo_customer = False
            woo_partner.unlink()
        return

    @http.route(["/update_coupon_webhook_odoo", "/restore_coupon_webhook_odoo"], csrf=False, auth="public", type="json")
    def update_coupon_webhook(self):
        """
        Route for handling the coupon update webhook of WooCommerce.
        @author: Haresh Mori on Date 2-Jan-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return

        update_webhook = bool(request.httprequest.path.split('/')[1] == "update_coupon_webhook_odoo")
        if update_webhook:
            _logger.info("UPDATE COUPON WEBHOOK call for this coupon: %s", res.get("code"))
        else:
            _logger.info("RESTORE COUPON WEBHOOK call for this coupon: %s", res.get("code"))
        request.env["woo.coupon.data.queue.ept"].sudo().create_coupon_queue_from_webhook(res, instance)

    @http.route("/delete_coupon_webhook_odoo", csrf=False, auth="public", type="json")
    def delete_coupon_webhook(self):
        """
        Route for handling the coupon delete webhook for WooCommerce
        @author: Haresh Mori on Date 2-Jan-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res, instance = self.get_basic_info()
        if not res:
            return
        _logger.info("DELETE COUPON WEBHOOK call for this coupon: %s", res)
        woo_coupon = request.env["woo.coupons.ept"].sudo().search(["&", "|", ('coupon_id', '=', res.get("id")),
                                                                   ('code', '=', res.get("code")),
                                                                   ('woo_instance_id', '=', instance.id)], limit=1)
        if woo_coupon and instance.active:
            woo_coupon.write({'active': False})

        return

    @staticmethod
    def get_basic_info():
        """
        This method is used return basic info. It will return res and instance.
        @author: Haresh Mori on Date 2-Jan-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res = request.get_json_data()
        headers = request.httprequest.headers
        host = headers.get("X-WC-Webhook-Source").rstrip('/')
        instance = request.env["woo.instance.ept"].sudo().search([("woo_host", "ilike", host)])

        if not instance:
            _logger.warning("Instance is not found for host %s, while searching for Webhook.", host)
            res = False
        return res, instance

# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger("WooCommerce")


class WooWebhookEpt(models.Model):
    """
    Model for storing webhooks created in woocommerce.
    @author: Maulik Barad on Date 30-Oct-2019.
    """
    _name = "woo.webhook.ept"
    _description = "WooCommerce Webhook"

    name = fields.Char(help="Name of Webhook created in woocommerce.", copy=False)
    woo_id = fields.Char(help="Id of webhook in woocommerce", copy=False, string="ID in Woo")
    topic = fields.Selection([("order.updated", "When Order is Created/Updated"),
                              ("order.deleted", "When Order is Deleted"),
                              ("product.updated", "When Product is Created/Updated"),
                              ("product.deleted", "When Product is Deleted"),
                              ("product.restored", "When Product is Restored"),
                              ("customer.updated", "When Customer is Created/Updated"),
                              ("customer.deleted", "When Customer is Deleted"),
                              ("coupon.updated", "When Coupon is Created/Updated"),
                              ("coupon.deleted", "When Coupon is Deleted"),
                              ("coupon.restored", "When Coupon is Restored")],
                             string="Action", help="Select action, when the webhook will be fired.")
    instance_id = fields.Many2one("woo.instance.ept", copy=False, help="Webhook created by this Woocommerce Instance.",
                                  ondelete="cascade")
    status = fields.Selection([("active", "Active"), ("paused", "Paused"), ("disabled", "Disabled")], copy=False,
                              default="active",
                              help="""Webhook statuses are :\nActive : delivers payload.\nPaused : delivery paused by
                              admin.\nDisabled : delivery paused by failure.""")
    delivery_url = fields.Char(help="URL where the webhook payload is delivered.")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherited for creating webhook in WooCommerce store for the same.
        @author: Maulik Barad on Date 20-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for vals in vals_list:
            available_webhook = self.search_read([("topic", "=", vals.get("topic")),
                                                  ("instance_id", "=", vals.get("instance_id"))], ["id"])
            if available_webhook:
                raise UserError(_("Webhook already exists for selected action: %s. You can't create webhook with same "
                                  "action. \nAction must be unique for the Instance." % vals.get("topic")))

        res = super(WooWebhookEpt, self).create(vals_list)
        for webhook in res:
            webhook.get_webhook()
        return res

    def unlink(self):
        """
        Inherited method for deleting the webhooks from WooCommerce Store.
        @author: Maulik Barad on Date 20-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        webhook_ids = self.mapped("woo_id")
        if webhook_ids:
            wc_api = self.instance_id.woo_connect()
            data = {"delete": webhook_ids}

            try:
                response = wc_api.post("webhooks/batch", data)
            except Exception as error:
                raise UserError(_("Something went wrong while deleting Webhook.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            if response.status_code not in [200, 201]:
                raise UserError("Something went wrong while deleting the webhook.\n" + str(
                    response.status_code) + "\n" + response.reason)

        _logger.info("Webhook deleted successfully.")
        return super(WooWebhookEpt, self).unlink()

    def toggle_status(self, status=False):
        """
        Toggles the webhook status between Active and Paused in woocommerce.
        @author: Maulik Barad on Date 01-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = self.instance_id.woo_connect()
        for hook in self:
            status = status if status else "paused" if hook.status == "active" else "active"
            try:
                response = wc_api.put("webhooks/" + str(hook.woo_id), {"status": status})
            except Exception as error:
                raise UserError(_("Something went wrong while Updating Webhook.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            if response.status_code in [200, 201]:
                hook.status = status
            else:
                raise UserError("Something went wrong while changing status of the webhook.\n" + str(
                    response.status_code) + "\n" + response.reason)
        _logger.info("Webhook status changed.")
        return True

    def get_delivery_url(self):
        """
        Gives delivery URL for the webhook as per the topic.
        @author: Maulik Barad on Date 20-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        delivery_url = ""
        topic = self.topic
        if topic == "order.updated":
            delivery_url = self.get_base_url() + "/update_order_webhook_odoo"
        elif topic == "order.deleted":
            delivery_url = self.get_base_url() + "/delete_order_webhook_odoo"
        elif topic == "product.updated":
            delivery_url = self.get_base_url() + "/update_product_webhook_odoo"
        elif topic == "product.deleted":
            delivery_url = self.get_base_url() + "/delete_product_webhook_odoo"
        elif topic == "product.restored":
            delivery_url = self.get_base_url() + "/restore_product_webhook_odoo"
        elif topic == "customer.updated":
            delivery_url = self.get_base_url() + "/update_customer_webhook_odoo"
        elif topic == "customer.deleted":
            delivery_url = self.get_base_url() + "/delete_customer_webhook_odoo"
        elif topic == "coupon.updated":
            delivery_url = self.get_base_url() + "/update_coupon_webhook_odoo"
        elif topic == "coupon.deleted":
            delivery_url = self.get_base_url() + "/delete_coupon_webhook_odoo"
        elif topic == "coupon.restored":
            delivery_url = self.get_base_url() + "/restore_coupon_webhook_odoo"
        return delivery_url

    def get_webhook(self):
        """
        Creates webhook in WooCommerce Store for webhook in Odoo if no webhook is
        there, otherwise updates status of the webhook, if it exists in WooCommerce store.
        @author: Maulik Barad on Date 20-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        topic = self.topic
        instance = self.instance_id
        wc_api = instance.woo_connect()
        delivery_url = self.get_delivery_url()

        webhook_data = {
            "name": self.name,
            "topic": topic,
            "status": "active",
            "delivery_url": delivery_url
        }
        if self.woo_id:
            # Checks for available webhook. Updates status if available otherwise deletes the webhook in Odoo.
            try:
                response = wc_api.get("webhooks/" + str(self.woo_id))
            except Exception as error:
                raise UserError(_("Something went wrong while checking the Webhooks.\n\nPlease Check your Connection "
                                  "and Instance Configuration.\n\n" + str(error)))

            if response.status_code == 200:
                self.status = response.json().get("status")
            else:
                self.woo_id = 0
                self.unlink()
            return True

        try:
            response = wc_api.post("webhooks", webhook_data)
        except Exception as error:
            raise UserError(_("Something went wrong while creating Webhooks.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        if response.status_code not in [200, 201]:
            raise UserError("Something went wrong while creating the webhook.\n" + str(
                response.status_code) + "\n" + response.reason)
        new_webhook = response.json()
        self.write({"woo_id": new_webhook.get("id"), "status": new_webhook.get("status"),
                    "delivery_url": delivery_url})
        _logger.info("Webhook created successfully.")
        return True

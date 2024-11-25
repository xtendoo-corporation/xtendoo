# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import models, fields

_logger = logging.getLogger("WooCommerce")


class CommonLogLinesEpt(models.Model):
    _inherit = "common.log.lines.ept"
    _rec_name = "message"

    woo_instance_id = fields.Many2one("woo.instance.ept", "Woo Instance")
    woo_customer_data_queue_line_id = fields.Many2one("woo.customer.data.queue.line.ept", "Woo Customer Queue Line")
    woo_order_data_queue_line_id = fields.Many2one("woo.order.data.queue.line.ept", "Woo Order Queue Line")
    woo_product_queue_line_id = fields.Many2one("woo.product.data.queue.line.ept", "Woo Product Queue Line")
    woo_coupon_data_queue_line_id = fields.Many2one("woo.coupon.data.queue.line.ept", "Woo Coupon Queue Line")
    woo_export_stock_queue_line_id = fields.Many2one("woo.export.stock.queue.line.ept")

    def woo_prepare_data_for_activity(self):
        """
        This method prepares necessary data from the log lines.
        @author: Maulik Barad on Date 10-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_order_data_queue_line_id:
            queue_lines = self.woo_order_data_queue_line_id.filtered(lambda x: x.state == "failed")
            queue_id = queue_lines.order_data_queue_id
            model_name = "woo.order.data.queue.ept"
            woo_order_list = queue_lines.mapped("woo_order")
            note = "Your order has not been imported for Woo Order Reference : %s" % str(woo_order_list)[1:-1]
        else:
            queue_lines = self.woo_product_queue_line_id.filtered(lambda x: x.state == "failed")
            queue_id = queue_lines.queue_id
            model_name = "woo.product.data.queue.ept"
            woo_order_list = queue_lines.mapped("woo_synced_data_id")
            note = "Your products has not been imported as Woo Products Reference : %s" % str(woo_order_list)[1:-1]

        return queue_id, woo_order_list, note, model_name

    def create_woo_schedule_activity(self, queue_id=False, model_name=False, queue_crash_activity=False):
        """
        @author: Haresh Mori on date 03/12/2019
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_order_list = []
        mail_activity_obj = self.env["mail.activity"]

        if queue_crash_activity:
            woo_instance = queue_id.woo_instance_id
            note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % queue_id.name
        else:
            woo_instance = self.woo_instance_id
            queue_id, woo_order_list, note, model_name = self.woo_prepare_data_for_activity()

        model_id = self.sudo()._get_model_id(model_name)

        activity_type_id = woo_instance.activity_type_id.id
        date_deadline = datetime.strftime(datetime.now() + timedelta(days=woo_instance.date_deadline), "%Y-%m-%d")

        if (note and woo_order_list) or queue_crash_activity:
            for user_id in woo_instance.user_ids:
                mail_activity = mail_activity_obj.search([("res_model_id", "=", model_id.id),
                                                          ("user_id", "=", user_id.id),
                                                          ("res_name", "=", queue_id.name),
                                                          ("activity_type_id", "=", activity_type_id)])
                if not mail_activity:
                    vals = {"activity_type_id": activity_type_id, "note": note, "res_id": queue_id.id,
                            "user_id": user_id.id, "res_model_id": model_id.id, "date_deadline": date_deadline}
                    try:
                        mail_activity_obj.create(vals)
                    except Exception:
                        _logger.info("Unable to create schedule activity, Please give proper "
                                     "access right of this user :%s  ", user_id.name)
        return True

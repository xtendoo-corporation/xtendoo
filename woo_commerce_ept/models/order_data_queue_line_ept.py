# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time

from datetime import datetime, timedelta

from odoo import fields, models

_logger = logging.getLogger("WooCommerce")


class WooOrderDataQueueLineEpt(models.Model):
    """
    Model for storing imported order data and creating sale orders that data.
    @author: Maulik Barad on Date 24-Oct-2019.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """
    _name = "woo.order.data.queue.line.ept"
    _description = "WooCommerce Order Data Queue Line"
    _rec_name = "number"

    order_data_queue_id = fields.Many2one("woo.order.data.queue.ept", ondelete="cascade")
    instance_id = fields.Many2one(related="order_data_queue_id.instance_id", copy=False,
                                  help="Order imported from this Woocommerce Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"),
                              ("cancel", "Cancelled"), ("done", "Done")], default="draft", copy=False)
    woo_order = fields.Char(help="Id of imported order.", copy=False)
    sale_order_id = fields.Many2one("sale.order", copy=False,
                                    help="Order created in Odoo.")
    order_data = fields.Text(help="Data imported from Woocommerce of current order.", copy=False)
    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed.", copy=False)
    common_log_lines_ids = fields.One2many("common.log.lines.ept", "woo_order_data_queue_line_id",
                                           help="Log lines created against which line.", string="Log Message")
    number = fields.Char(string="Order Number")

    def open_sale_order(self):
        """
        Returns action for opening the related sale order.
        @author: Maulik Barad on Date 24-Oct-2019.
        @return: Action to open sale order record.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return {
            "name": "Sale Order",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "views": [(False, "form")],
            "context": self.env.context
        }

    def auto_order_queue_lines_process(self):
        """
        This method use to find a order queue line records .
        @param : self
        @author: Haresh Mori @Emipro Technologies Pvt.Ltd on date 02/12/2019.
        Task Id : 158314
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_queue_ids = []
        woo_order_data_queue_obj = self.env["woo.order.data.queue.ept"]
        start = time.time()

        self.env.cr.execute(
            """update woo_order_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        query = """select queue.id from woo_order_data_queue_line_ept as queue_line
                inner join woo_order_data_queue_ept as queue on queue_line.order_data_queue_id = queue.id
                where queue_line.state='draft' and queue.is_action_require = 'False'
                ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        order_queue_list = self._cr.fetchall()
        for result in order_queue_list:
            order_queue_ids.append(result[0])

        if order_queue_ids:
            order_queues = woo_order_data_queue_obj.browse(list(set(order_queue_ids)))

            order_queue_process_cron_time = order_queues.instance_id.get_woo_cron_execution_time(
                "woo_commerce_ept.process_woo_order_data_queue")
            for order_queue_id in order_queues:
                order_queue_lines = order_queue_id.order_data_queue_line_ids.filtered(lambda x: x.state == "draft")
                order_queue_id.queue_process_count += 1
                if order_queue_id.queue_process_count > 3:
                    order_queue_id.is_action_require = True
                    note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % (
                        order_queue_id.name)
                    order_queue_id.message_post(body=note)
                    if order_queue_id.instance_id.is_create_schedule_activity:
                        self.create_order_queue_schedule_activity(order_queue_id)
                    continue

                self._cr.commit()
                if order_queue_lines:
                    order_queue_lines.process_order_queue_line()
                if time.time() - start > order_queue_process_cron_time - 60:
                    break
        return True

    def create_order_queue_schedule_activity(self, queue_id):
        """
        This method is used to create a schedule activity for queue.
        @:parameter : queue_id : it is object of queue
        Author: Nilesh Parmar
        Date: 28 january 2020.
        task id : 160199
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_model_obj = self.env["ir.model"]
        mail_activity_obj = self.env["mail.activity"]
        model_id = ir_model_obj.search([("model", "=", "woo.order.data.queue.ept")])
        activity_type_id = queue_id.instance_id.activity_type_id.id
        date_deadline = datetime.strftime(datetime.now() + timedelta(days=queue_id.instance_id.date_deadline),
                                          "%Y-%m-%d")
        if queue_id:
            note = "Attention %s queue is processed 3 times you need to process it manually" % queue_id.name
            for user_id in queue_id.instance_id.user_ids:
                mail_activity = mail_activity_obj.search([("res_model_id", "=", model_id.id),
                                                          ("user_id", "=", user_id.id),
                                                          ("res_name", "=", queue_id.name),
                                                          ("activity_type_id", "=", activity_type_id)])
                if not mail_activity:
                    vals = {"activity_type_id": activity_type_id,
                            "note": note, "res_id": queue_id.id,
                            "user_id": user_id.id, "res_model_id": model_id.id,
                            "date_deadline": date_deadline}
                    try:
                        mail_activity_obj.create(vals)
                    except Exception:
                        _logger.info("Unable to create schedule activity, Please give proper "
                                     "access right of this user :%s  ", user_id.name)
        return True

    def process_order_queue_line(self, update_order=False):
        """
        Process the imported order data and create the order.
        @author: Haresh Mori on Date 24-Oct-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = log_line = self.env["common.log.lines.ept"]
        sale_order_obj = self.env["sale.order"]
        start = time.time()
        queue_id = self.order_data_queue_id

        if queue_id.created_by == 'webhook':
            update_order = True

        if update_order:
            log_line = sale_order_obj.update_woo_order(self, queue_id.instance_id)
        else:
            log_line = sale_order_obj.create_woo_orders(self)

        if log_line and queue_id.instance_id.is_create_schedule_activity:
            common_log_line_obj.create_woo_schedule_activity()

        end = time.time()
        _logger.info("Processed %s orders in %s seconds.", str(len(self)), str(end - start))
        return True

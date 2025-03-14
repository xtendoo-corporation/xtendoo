#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store Order Data queue line
"""
import json
import time
import logging
from datetime import timedelta, datetime
from odoo import models, fields

_logger = logging.getLogger(__name__)


class EbayOrderDataQueueLineEpt(models.Model):
    """
    Describes Order Data Queue Line
    """
    _name = "ebay.order.data.queue.line.ept"
    _description = "Ebay Order Data Queue Line EPT"
    _rec_name = "ebay_order_id"
    ebay_order_data_queue_id = fields.Many2one("ebay.order.data.queue.ept")
    seller_id = fields.Many2one('ebay.seller.ept', string='Seller', help="Order imported from this Ebay Instance.")
    state = fields.Selection([
        ("draft", "Draft"), ("failed", "Failed"), ("done", "Done"), ("cancel", "Cancelled")
    ], default="draft", copy=False)
    ebay_order_id = fields.Char(string="eBay Order Id", help="Id of imported order.", copy=False)
    sale_order_id = fields.Many2one("sale.order", string="Odoo Order Id", copy=False, help="Order created in Odoo.")
    order_data = fields.Text(string="eBay Order Data", help="Data imported from eBay of current order.", copy=False)
    processed_at = fields.Datetime(
        string="Order Processed At", help="Shows Date and Time, When the data is processed", copy=False)
    ebay_order_common_log_lines_ids = fields.One2many(
        "common.log.lines.ept", "ebay_order_data_queue_line_id", string="eBay Order Common Log lines",
        help="Log lines created against which line.")
    is_import_shipped_order = fields.Boolean(string="Is import eBay shipped order?", default=False)

    def create_order_data_queue_line(self, order_response, seller, order_type):
        """
        Creates a order data queue line and splits order queue line after 50 orders.
        :param order_response: order data received from eBay
        :param seller: seller of eBay
        :param order_queue_data: Dictionary of order queue count,total queue and is order queue boolean.
        """
        order_queue_list = []
        is_create_queue = True
        count = 0
        for order in order_response:
            ebay_order_ref = order.get('OrderID', False)
            if not ebay_order_ref:
                continue
            if is_create_queue:
                order_queue = self.ebay_create_order_queue(seller, order_type)
                _logger.info("Created new order queue: %s" % order_queue.name)
                order_queue_list.append(order_queue.id)
                is_create_queue = False
                self._cr.commit()
            data = json.dumps(order)
            _logger.info("Adding order ID:%s data in queue: %s" % (ebay_order_ref, order_queue.name))
            vals = self.prepare_order_queue_line_values(ebay_order_ref, seller, data, order_queue)
            self.create(vals)
            count = count + 1
            if count == 50:
                count = 0
                is_create_queue = True
        return order_queue_list

    def prepare_order_queue_line_values(self, ebay_order_ref, seller, data, order_queue):
        """
        This method is use to prepare order queue line data.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 5 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        order_queue_line_values = {
            'ebay_order_id': ebay_order_ref,
            'seller_id': seller and seller.id or False,
            'order_data': data,
            'ebay_order_data_queue_id': order_queue.id,
            'state': 'draft',
            'is_import_shipped_order': True
        }
        return order_queue_line_values

    def ebay_create_order_queue(self, seller, order_type):
        """
        This method used to create a order queue as per the split requirement of the
        queue. It is used for process the queue manually.
        :param seller: seller of eBay
        Migration done by Haresh Mori @ Emipro on date 5 January 2022 .
        """
        order_queue_values = {'seller_id': seller and seller.id or False, 'state': 'draft', 'queue_type': order_type}
        order_queue = self.env["ebay.order.data.queue.ept"].create(order_queue_values)
        return order_queue

    def auto_start_child_process_for_order_queue(self):
        """
        This method used to start the child process cron for process the order queue line data.
        """
        child_order_queue_cron = self.env.ref('ebay_ept.ir_cron_child_to_process_order_queue')
        if child_order_queue_cron and not child_order_queue_cron.active:
            results = self.search([('state', '=', 'draft')], limit=100)
            if results:
                child_order_queue_cron.write({
                    'active': True, 'numbercall': 1, 'nextcall': datetime.now() + timedelta(seconds=10)})
        return True

    def auto_import_order_queue_data(self):
        """
        This method used to process synced shopify order data in batch of 50 queue lines.
        This method is called from cron job.
        """
        order_queue_ids = []
        ebay_import_order_queue_obj = self.env["ebay.order.data.queue.ept"]
        query = """select queue.id from ebay_order_data_queue_line_ept as queue_line
                        inner join ebay_order_data_queue_ept as queue on queue_line.ebay_order_data_queue_id = queue.id
                        where queue_line.state=%s and queue.is_action_require = %s
                        ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query, ('draft', 'False'))
        order_data_queue_list = self._cr.fetchall()
        for result in order_data_queue_list:
            order_queue_ids.append(result[0])
        if not order_queue_ids:
            return True
        order_queues = ebay_import_order_queue_obj.browse(list(set(order_queue_ids)))
        self.process_order_queue_and_post_message(order_queues)
        return True

    def process_order_queue_and_post_message(self, order_queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the product queue line.
        :param order_queues: eBay import product queue object
        """
        start = time.time()
        order_queue_process_cron_time = order_queues.seller_id.get_ebay_cron_execution_time(
            "ebay_ept.ir_cron_child_to_process_order_queue")
        for order_queue in order_queues:
            order_data_queue_line_ids = order_queue.order_data_queue_line_ids

            # For counting the queue crashes for the queue.
            order_queue.queue_process_count += 1
            if order_queue.queue_process_count > 3:
                order_queue.is_action_require = True
                note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % \
                       order_queue.name
                order_queue.message_post(body=note)
                return True
            self._cr.commit()
            order_data_queue_line_ids.process_import_order_queue_data()
            if time.time() - start > order_queue_process_cron_time - 60:
                return True
        return True

    def process_import_order_queue_data(self):
        """
        This method processes order queue lines.
        Migration done by Haresh Mori @ Emipro on date 6 January 2022 .
        """
        sale_order_obj = self.env['sale.order']
        queue_id = self.ebay_order_data_queue_id
        if queue_id:
            seller_id = queue_id.seller_id
            qry = """update ebay_order_data_queue_ept set is_process_queue = False
                where is_process_queue = True and id = %s"""
            self._cr.execute(qry, (queue_id.id,))
            self._cr.commit()
            for order_queue_line in self:
                sale_order_obj.create_ebay_sales_order_ept(seller_id, order_queue_line, queue_id)
                queue_id.is_process_queue = False
        return True

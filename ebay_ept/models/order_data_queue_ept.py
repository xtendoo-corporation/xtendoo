#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay import order data queue.
"""
import logging
from datetime import timedelta, datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EbayOrderDataQueueEpt(models.Model):
    """
    Describes eBay Order Data Queue
    """
    _name = "ebay.order.data.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Ebay Order Data Queue EPT"
    _order = "name desc"

    name = fields.Char(string="Order Queue Name", help="Sequential name of imported order.", copy=False)
    seller_id = fields.Many2one('ebay.seller.ept', string='Seller', help="Order imported from this Ebay Seller.")
    state = fields.Selection([
        ('draft', 'Draft'), ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed'), ('failed', 'Failed')
    ], default='draft', copy=False, help="Status of Order Data Queue", compute="_compute_queue_state", store=True)
    order_common_log_book_id = fields.Many2one(
        "common.log.book.ept", string="Order Queue logs", help="Related Log book which has all logs for current queue.")
    ebay_order_common_log_lines_ids = fields.One2many(
        related="order_data_queue_line_ids.ebay_order_common_log_lines_ids", help="Log lines of Common log book for particular order queue")
    order_data_queue_line_ids = fields.One2many(
        "ebay.order.data.queue.line.ept", "ebay_order_data_queue_id", help="Order data queue line ids")
    order_queue_line_total_record = fields.Integer(
        string='Total Records', compute='_compute_order_queue_line_record',
        help="Returns total number of order data queue lines")
    order_queue_line_draft_record = fields.Integer(
        string='Draft Records', compute='_compute_order_queue_line_record',
        help="Returns total number of draft order data queue lines")
    order_queue_line_fail_record = fields.Integer(
        string='Fail Records', compute='_compute_order_queue_line_record',
        help="Returns total number of Failed order data queue lines")
    order_queue_line_done_record = fields.Integer(
        string='Done Records', compute='_compute_order_queue_line_record',
        help="Returns total number of done order data queue lines")
    order_queue_line_cancel_record = fields.Integer(
        string='Cancel Records', compute='_compute_order_queue_line_record',
        help="Returns total number of cancel order data queue lines")
    is_process_queue = fields.Boolean(string='Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False)
    queue_process_count = fields.Integer(
        string="Queue Process Times", help="It is used know queue how many time processed")
    queue_type = fields.Selection([("shipped", "Shipped Order Queue"), ("unshipped", "Unshipped Order Queue")],
                                  help="Identify to queue for which type of order import.")

    @api.depends('order_data_queue_line_ids.state')
    def _compute_queue_state(self):
        """
        Computes state from different states of queue lines.
        """
        for record in self:
            total_record = record.order_queue_line_total_record
            if total_record == record.order_queue_line_done_record + record.order_queue_line_cancel_record:
                record.state = "completed"
            elif total_record == record.order_queue_line_draft_record:
                record.state = "draft"
            elif total_record == record.order_queue_line_fail_record:
                record.state = "failed"
            else:
                record.state = "partially_completed"

    def _compute_order_queue_line_record(self):
        """
        This will calculate total, draft, failed and done orders from ebay.
        """
        for order_queue in self:
            order_queue.order_queue_line_total_record = len(order_queue.order_data_queue_line_ids)
            order_queue.order_queue_line_draft_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'draft'))
            order_queue.order_queue_line_fail_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'failed'))
            order_queue.order_queue_line_done_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'done'))
            order_queue.order_queue_line_cancel_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'cancel'))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates a sequence for Ordered Data Queue
        :param vals_list: values to create Ordered Data Queue
        :return: EbayOrderDataQueueEpt Object
        """
        for vals in vals_list:
            sequence_id = self.env.ref('ebay_ept.seq_order_queue_data').ids
            if sequence_id:
                order_data_queue_sequence = self.env['ir.sequence'].browse(sequence_id).next_by_id()
            else:
                order_data_queue_sequence = '/'
            vals.update({'name': order_data_queue_sequence or ''})
        return super(EbayOrderDataQueueEpt, self).create(vals_list)

    def import_unshipped_orders_from_ebay(self, seller):
        """
        This method is use to get unshipped orders from ebay store to Odoo and create order data queue.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 5 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        order_queues_list = []
        order_queue_line_obj = self.env["ebay.order.data.queue.line.ept"]
        from_date, to_date = self.calculate_order_from_and_to_date(seller, False, False)
        page_number = 1
        trade_api_param = {'ModTimeFrom': from_date, 'ModTimeTo': to_date, 'OrderStatus': 'Completed',
                           'OrderRole': 'Seller', 'DetailLevel': 'ReturnAll',
                           'Pagination': {'PageNumber': page_number, 'EntriesPerPage': 100}}
        while True:
            order_response, has_more_orders = self.get_sale_orders_from_ebay(seller, trade_api_param)
            if order_response:
                order_queues = order_queue_line_obj.create_order_data_queue_line(order_response, seller, 'unshipped')
                order_queues_list += order_queues
                order_queue_cron = self.env.ref("ebay_ept.ir_cron_child_to_process_order_queue")
                if not order_queue_cron.active:
                    _logger.info("Active the order queue cron job")
                    order_queue_cron.write({'active': True, 'nextcall': datetime.now() + timedelta(seconds=120)})
            page_number = page_number + 1
            trade_api_param.get('Pagination').update({'PageNumber': page_number})
            if has_more_orders == 'false':
                seller.write({'last_ebay_order_import_date': datetime.now()})
                break
        return order_queues_list

    def import_shipped_orders_from_ebay(self, seller, shipped_order_to_date, shipped_order_from_date):
        """
        This method is use to get shipped orders from ebay store to Odoo and create order data queue.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 5 January 2022 .
        Task_id:180141 - Import Shipped Orders
        """
        order_queues_list = []
        order_queue_line_obj = self.env["ebay.order.data.queue.line.ept"]
        from_date, to_date = self.calculate_order_from_and_to_date(seller, shipped_order_to_date,
                                                                   shipped_order_from_date)
        page_number = 1
        trade_api_param = {'CreateTimeFrom': from_date, 'CreateTimeTo': to_date, 'OrderStatus': 'Completed',
                           'OrderRole': 'Seller', 'DetailLevel': 'ReturnAll',
                           'Pagination': {'PageNumber': page_number, 'EntriesPerPage': 100}}
        while True:
            order_response, has_more_orders = self.get_sale_orders_from_ebay(seller, trade_api_param,
                                                                             is_shipped_order=True)
            if order_response:
                order_queues = order_queue_line_obj.create_order_data_queue_line(order_response, seller, 'shipped')
                order_queues_list += order_queues
                order_queue_cron = self.env.ref("ebay_ept.ir_cron_child_to_process_order_queue")
                if not order_queue_cron.active:
                    _logger.info("Active the order queue cron job")
                    order_queue_cron.write({'active': True, 'nextcall': datetime.now() + timedelta(seconds=120)})
            page_number = page_number + 1
            trade_api_param.get('Pagination').update({'PageNumber': page_number})
            if has_more_orders == 'false':
                break
        return order_queues_list

    @staticmethod
    def calculate_order_from_and_to_date(seller, shipped_order_to_date, shipped_order_from_date):
        """
        Calculate order from date and to date.
        :param seller: eBay seller object.
        :param shipped_order_from_date: Date from which order will import from eBay
        :param shipped_order_to_date: order will import from eBay till this date
        Migration done by Haresh Mori @ Emipro on date 5 January 2022 .
        """
        ebay_date_time_format = "%Y-%m-%dT%H:%M:%S.000Z"
        if shipped_order_to_date:
            to_date = shipped_order_to_date.strftime(ebay_date_time_format)
        else:
            to_date = seller.get_ebay_official_time()
        if shipped_order_from_date:
            current_date = seller.get_ebay_official_time()
            max_allow_time = datetime.strptime(current_date, ebay_date_time_format) - timedelta(days=90)
            max_allow_date = max_allow_time.strftime(ebay_date_time_format)
            from_date = shipped_order_from_date.strftime(ebay_date_time_format)
            if from_date < max_allow_date:
                raise UserError(_("Select From Date after %s", max_allow_time.strftime("%Y-%m-%d")))
        else:
            if seller.last_ebay_order_import_date:
                from_date = seller.last_ebay_order_import_date - timedelta(days=int(seller.order_import_days))
                from_date = str(from_date.strftime("%Y-%m-%dT%H:%M:%S")) + '.000Z'
            else:
                current_time = datetime.strptime(to_date, ebay_date_time_format) - timedelta(days=30)
                from_date = current_time.strftime(ebay_date_time_format)
        return from_date, to_date

    @staticmethod
    def get_sale_orders_from_ebay(seller, trade_api_param, is_shipped_order=False):
        """
        Get Orders those have status is completed from eBay via GetOrders API
        :param seller: eBay seller object
        :return: Dictionary of Shipped or Unshipped orders and True/False for hasMoreOrders
        Migration done by Haresh Mori @ Emipro on date 5 January 2022 .
        """
        order_response = []
        try:
            trade_api = seller.get_trading_api_object()
            trade_api.execute('GetOrders', trade_api_param)
            results = trade_api.response.dict()
            orders = []
            if results.get('OrderArray', {}) and results['OrderArray'].get('Order', []):
                orders = results['OrderArray'].get('Order', [])
        except Exception as error:
            raise UserError(error)
        if isinstance(orders, dict):
            orders = [orders]
        for result in orders:
            if not result.get('ShippedTime') and not is_shipped_order:
                order_response.append(result)
            elif result.get('ShippedTime') and is_shipped_order:
                order_response.append(result)
        return order_response, results.get('HasMoreOrders', 'false')

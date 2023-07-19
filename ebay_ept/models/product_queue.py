#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for sync/ Import product queues.
"""
import json
import logging

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SyncImportProductQueue(models.Model):
    """
    Describes sync/ Import product queues.
    """
    _name = "ebay.import.product.queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Sync/ Import Product Queue"
    _order = "name desc"

    name = fields.Char(help="Sequential name of imported/ Synced products.", copy=False)
    seller_id = fields.Many2one(
        'ebay.seller.ept', string='Seller', help="Product imported from or Synced to this Ebay Seller.")
    state = fields.Selection([
        ('draft', 'Draft'), ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed'), ('failed', 'Failed')
    ], default='draft', copy=False, help="Status of Order Data Queue", compute="_compute_queue_state", store=True)
    import_product_common_log_lines_ids = fields.One2many(
        related="import_product_queue_line_ids.import_product_common_log_lines_ids",
        help="Log lines of Common log book for particular product queue")
    import_product_queue_line_ids = fields.One2many(
        "ebay.import.product.queue.line", "sync_import_product_queue_id", help="Sync/ Import product queue line ids")
    import_product_queue_line_total = fields.Integer(
        string='Total Records', compute='_compute_product_queue_line_record',
        help="Returns total number of Sync/Import product queue lines")
    import_product_queue_line_draft = fields.Integer(
        string='Draft Records', compute='_compute_product_queue_line_record',
        help="Returns total number of draft Sync/Import product queue lines")
    import_product_queue_line_fail = fields.Integer(
        string='Fail Records', compute='_compute_product_queue_line_record',
        help="Returns total number of Failed Sync/Import product queue lines")
    import_product_queue_line_done = fields.Integer(
        string='Done Records', compute='_compute_product_queue_line_record',
        help="Returns total number of done Sync/Import product queue lines")
    import_product_queue_line_cancel = fields.Integer(
        string='Cancel Records', compute='_compute_product_queue_line_record',
        help="Returns total number of cancel Sync/Import product queue lines")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(string="Queue Running Status", default="Running...")
    is_action_require = fields.Boolean(default=False)
    queue_process_count = fields.Integer(
        string="Queue Process Times", help="it is used know queue how many time processed")

    @api.depends('import_product_queue_line_ids.state')
    def _compute_queue_state(self):
        """
        Computes state from different states of queue lines.
        """
        for record in self:
            total_record = record.import_product_queue_line_total
            if total_record == record.import_product_queue_line_done + record.import_product_queue_line_cancel:
                record.state = "completed"
            elif total_record == record.import_product_queue_line_draft:
                record.state = "draft"
            elif total_record == record.import_product_queue_line_fail:
                record.state = "failed"
            else:
                record.state = "partially_completed"

    def _compute_product_queue_line_record(self):
        """
        This will calculate total, draft, failed and done products sync/import from ebay.
        """
        for product_queue in self:
            product_queue.import_product_queue_line_total = len(
                product_queue.import_product_queue_line_ids)
            product_queue.import_product_queue_line_draft = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'draft'))
            product_queue.import_product_queue_line_fail = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'failed'))
            product_queue.import_product_queue_line_done = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'done'))
            product_queue.import_product_queue_line_cancel = len(
                product_queue.import_product_queue_line_ids.filtered(lambda x: x.state == 'cancel'))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates a sequence for Ordered Data Queue
        :param vals_list: values to create Ordered Data Queue
        :return: EbayOrderDataQueueEpt Object
        """
        for vals in vals_list:
            sequence_id = self.env.ref('ebay_ept.seq_import_product_queue_data').ids
            if sequence_id:
                product_data_queue_sequence = self.env['ir.sequence'].browse(sequence_id).next_by_id()
            else:
                product_data_queue_sequence = '/'
            vals.update({'name': product_data_queue_sequence or ''})
        return super(SyncImportProductQueue, self).create(vals_list)

    def create_product_queue(self, seller, results, product_queue=False, is_create_odoo_product=False,
                             is_sync_stock=False, is_sync_price=False):
        """
        This method is use to create product queue.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        bus_bus_obj = self.env["bus.bus"]
        product_queue_line = self.env['ebay.import.product.queue.line']
        product_queues = []
        count = 0
        for item in results:
            if not product_queue:
                product_queue = product_queue_line.ebay_create_product_queue(seller)
                _logger.info("Created a new product queue: %s" % product_queue.name)
                message = "Product Queue created {}".format(product_queue.name)
                bus_bus_obj._sendone(self.env.user.partner_id, "simple_notification",
                                     {"title": "eBay Notification", "message": message, "sticky": False,
                                      "warning": True})
                last_product_queue = product_queue
                product_queues.append(product_queue.id)

            item_id = item.get('ItemID', False)
            data = json.dumps(item)
            val = product_queue_line.prepare_queue_line_vals(seller, item_id, data, product_queue,
                                                             is_create_odoo_product, is_sync_stock,
                                                             is_sync_price)
            _logger.info("Added data in Queue %s and Item Id: %s", product_queue.name, item_id)
            product_queue_line.create(val)
            count = count + 1
            if count == 50 or len(product_queue.import_product_queue_line_ids) == 50:
                count = 0
                product_queue = False
        return product_queues, last_product_queue

    def create_sync_import_product_queues(self, instance, from_date, to_date, product_queue_data,
                                          is_create_auto_odoo_product=False, is_sync_stock=False, is_sync_price=False):
        """
        This method is import the products and create product queue.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 January 2022 .
        """

        from_date = "%sT00:00:00.000Z" % from_date
        to_date = "%sT00:00:00.000Z" % to_date
        page_number = 1
        result_final = []
        while True:
            products = {}
            try:
                trade_api = instance.get_trading_api_object()
                para = {
                    'DetailLevel': 'ItemReturnDescription', 'StartTimeFrom': from_date, 'StartTimeTo': to_date,
                    'IncludeVariations': True, 'Pagination': {'EntriesPerPage': 100, 'PageNumber': page_number},
                    'IncludeWatchCount': True}
                trade_api.execute('GetSellerList', para)
                results = trade_api.response.dict()
                if results and results.get('Ack', False) == 'Success' and results.get('ItemArray', {}):
                    products = results['ItemArray'].get('Item', [])
            except Exception as error:
                raise UserError(_('%s', str(error)))
            has_more_trans = results.get('HasMoreItems', 'false')
            if isinstance(products, dict):
                products = [products]
            for result in products:
                result_final = result_final + [result]
            if has_more_trans == 'false':
                break
            page_number = page_number + 1
        if result_final:
            product_queue_data = self.env["ebay.import.product.queue.line"].create_import_product_queue_line(
                result_final, instance, product_queue_data, is_create_auto_odoo_product, is_sync_stock, is_sync_price)
        instance.last_ebay_catalog_import_date = datetime.now()
        return product_queue_data

    def dummy_function(self):
        """
        just show the buttons with count and
        user click on those button no need to do anything
        """
        return True

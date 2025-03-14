#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store sync/ Import product queue line
"""
import json
import time
from datetime import datetime
from odoo import models, fields


class SyncImportProductQueueLine(models.Model):
    """
    Describes sync/ Import product Queue Line
    """
    _name = "ebay.import.product.queue.line"
    _description = "Sync/ Import Product Queue Line"
    _rec_name = "ebay_item_id"
    sync_import_product_queue_id = fields.Many2one("ebay.import.product.queue")
    seller_id = fields.Many2one(
        'ebay.seller.ept', string='Seller', help="Products imported from or Synced to this Ebay Seller.")
    state = fields.Selection([
        ("draft", "Draft"), ("failed", "Failed"), ("done", "Done"), ("cancel", "Cancelled")
    ], default="draft", copy=False)
    ebay_item_id = fields.Char(help="Id of imported product item.", copy=False)
    product_data = fields.Text(help="Data imported from eBay of current item.", copy=False)
    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed", copy=False)
    import_product_common_log_lines_ids = fields.One2many(
        "common.log.lines.ept", "import_product_queue_line_id", help="Log lines created against which line.")
    is_create_auto_odoo_product = fields.Boolean(
        "Is product created in Odoo automatically?", default=False,
        help="Is product created in Odoo automatically when Sync/import products?")
    is_sync_stock = fields.Boolean(
        "Is product stock synced?", default=False, help="Is product stock synced when Sync/import products?")
    is_sync_price = fields.Boolean(
        "Is product price synced?", default=False, help="Is product price synced when Sync/import products?")

    def create_import_product_queue_line(self, items, instance, product_queue_data, is_create_auto_odoo_product=False,
                                         is_sync_stock=False, is_sync_price=False):
        """
        Creates a order data queue line and splits order queue line after 50 orders.
        :param items: item data received from eBay
        :param instance: instance of eBay
        :param product_queue_data: Dictionary of product queue count,total queue and is product queue boolean.
        :param is_create_auto_odoo_product: if true, then product will be created in Odoo
                                            automatically when Sync/import products
        :param is_sync_stock: if true, then product stock will be synced in Odoo
                                            automatically when Sync/import products
        :param is_sync_price: if true, then product price will be synced in Odoo
                                            automatically when Sync/import products
        """
        product_queue = product_queue_data.get('product_queue')
        count = product_queue_data.get('count')
        total_product_queues = product_queue_data.get('total_product_queues')

        for item in items:
            if item:
                if not product_queue:
                    product_queue = self.ebay_create_product_queue(instance.seller_id)
                    total_product_queues += 1
                item_id = item.get('ItemID', False)
                product_queue_line_values = {}
                data = json.dumps(item)
                product_queue_line_values.update({
                    'ebay_item_id': item_id,
                    'seller_id': instance and instance.seller_id.id or False,
                    'product_data': data,
                    'sync_import_product_queue_id': product_queue and product_queue.id or False,
                    'state': 'draft',
                    'is_create_auto_odoo_product': is_create_auto_odoo_product,
                    'is_sync_stock': is_sync_stock,
                    'is_sync_price': is_sync_price,
                })
                self.create(product_queue_line_values)
                count = count + 1
                if count == 50:
                    count = 0
                    product_queue = False
        product_queue_data.update({
            'product_queue': product_queue,
            'count': count,
            'total_product_queues': total_product_queues
        })
        return product_queue_data

    def ebay_create_product_queue(self, seller):
        """
        This method used to create a product queue as per the split requirement of the
        queue. It is used for process the queue manually.
        :param instance: instance of eBay
        """
        product_queue_vals = {
            'seller_id': seller and seller.id or False,
            'state': 'draft'}
        product_queue_data_id = self.env["ebay.import.product.queue"].create(product_queue_vals)
        return product_queue_data_id

    def auto_import_product_queue_data(self):
        """
        This method used to process synced eBay product data in batch of 50 queue lines.
        This method is called from cron job.
        """
        product_queue_ids = []
        ebay_import_product_queue_obj = self.env["ebay.import.product.queue"]
        query = """select queue.id from ebay_import_product_queue_line as queue_line
                inner join ebay_import_product_queue as queue on queue_line.sync_import_product_queue_id = queue.id
                where queue_line.state=%s and queue.is_action_require = %s
                ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query, ('draft', 'False'))
        product_data_queue_list = self._cr.fetchall()
        for result in product_data_queue_list:
            product_queue_ids.append(result[0])
        if not product_queue_ids:
            return True
        product_queues = ebay_import_product_queue_obj.browse(list(set(product_queue_ids)))
        self.process_product_queue_and_post_message(product_queues)
        return True

    def process_product_queue_and_post_message(self, product_queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the product queue line.
        :param product_queues: eBay import product queue object
        """
        start = time.time()
        product_queue_process_cron_time = product_queues.seller_id.get_ebay_cron_execution_time(
            "ebay_ept.ir_cron_child_to_process_product_queue")
        for product_queue in product_queues:
            product_data_queue_line_ids = product_queue.import_product_queue_line_ids

            # For counting the queue crashes for the queue.
            product_queue.queue_process_count += 1
            if product_queue.queue_process_count > 3:
                product_queue.is_action_require = True
                note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % \
                       product_queue.name
                product_queue.message_post(body=note)
                return True
            self._cr.commit()
            product_data_queue_line_ids.process_import_product_queue_data()
            if time.time() - start > product_queue_process_cron_time - 60:
                return True
        return True

    def process_import_product_queue_data(self):
        """
        This method is use to prepare product data queue and create products.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        product_listing_obj = self.env['ebay.product.listing.ept']
        queue_id = self.sync_import_product_queue_id
        if queue_id:
            qry = """update ebay_import_product_queue set is_process_queue = False
                where is_process_queue = True and id = %s"""
            self._cr.execute(qry, (queue_id.id,))
            self._cr.commit()
            count = 0
            for product_queue_line in self:
                count += 1
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': False})
                product_listing_obj.sync_product_listings(product_queue_line)
                queue_id.is_process_queue = False
                if self.env.context.get('is_product_queue_fail'):
                    product_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                else:
                    product_queue_line.write({'state': 'done', 'processed_at': datetime.now()})
                if count == 10:
                    self._cr.commit()
                    count = 0
        return True

    def prepare_queue_line_vals(self, seller, item_id, data, product_queue, is_create_odoo_product, is_sync_stock,
                                is_sync_price):
        """
        This method is use to prepare product data queue line.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        product_queue_line_values = ({
            'ebay_item_id': item_id,
            'seller_id': seller and seller.id or False,
            'product_data': data,
            'sync_import_product_queue_id': product_queue and product_queue.id or False,
            'state': 'draft',
            'is_create_auto_odoo_product': is_create_odoo_product,
            'is_sync_stock': is_sync_stock,
            'is_sync_price': is_sync_price,
        })
        return product_queue_line_values

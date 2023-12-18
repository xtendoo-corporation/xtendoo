# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time
import json

from odoo import models, fields

_logger = logging.getLogger("WooCommerce")


class WooProductDataQueueLineEpt(models.Model):
    _name = "woo.product.data.queue.line.ept"
    _description = 'WooCommerce Product Data Queue Line'

    woo_instance_id = fields.Many2one('woo.instance.ept', string='Instance')
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'),
                              ("cancel", "Cancelled"), ('done', 'Done')],
                             default='draft')
    synced_date = fields.Datetime(readonly=True)
    last_process_date = fields.Datetime(readonly=True)
    woo_synced_data = fields.Char(string='WooCommerce Synced Data')
    woo_synced_data_id = fields.Char(string='Data Id')
    queue_id = fields.Many2one('woo.product.data.queue.ept', ondelete="cascade")
    common_log_lines_ids = fields.One2many("common.log.lines.ept", "woo_product_queue_line_id",
                                           help="Log lines created against which line.")
    woo_update_product_date = fields.Char('Product Update Date')
    name = fields.Char(string="Product", help="It contain the name of product")
    image_import_state = fields.Selection([('pending', 'Pending'), ('done', 'Done')], default='done',
                                          help="It used to identify that product image imported explicitly")

    def sync_woo_product_data(self):
        """
        This method used to process synced Woo Commerce data.This method called from cron
        and manually from synced Woo Commerce data.
        @author: Dipak Gogiya @Emipro Technologies Pvt.Ltd
        Change by Nilesh Parmar 12/02/2020 for add the functionality to manage crash queue.
        if queue is crashed 3 times than create a schedule activity.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_data_queue_ids = []
        common_log_line_obj = self.env["common.log.lines.ept"]
        product_data_queue_obj = self.env['woo.product.data.queue.ept']
        start = time.time()

        query = """select queue.id from woo_product_data_queue_line_ept as queue_line
                            inner join woo_product_data_queue_ept as queue on queue_line.queue_id = queue.id
                            where queue_line.state='draft' and queue.is_action_require = 'False'
                            ORDER BY queue_line.create_date"""
        self._cr.execute(query)
        product_data_queue_list = self._cr.fetchall()
        if not product_data_queue_list:
            return False

        for result in product_data_queue_list:
            if result[0] not in product_data_queue_ids:
                product_data_queue_ids.append(result[0])

        product_queues = product_data_queue_obj.browse(product_data_queue_ids)
        product_queue_process_cron_time = product_queues.woo_instance_id.get_woo_cron_execution_time(
            "woo_commerce_ept.process_woo_product_data")
        for product_queue in product_queues:
            product_queue_line_ids = product_queue.queue_line_ids.filtered(lambda x: x.state == "draft")

            product_queue.queue_process_count += 1
            if product_queue.queue_process_count > 3:
                product_queue.is_action_require = True
                note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % (
                    product_queue.name)
                product_queue.message_post(body=note)
                if product_queue.woo_instance_id.is_create_schedule_activity:
                    common_log_line_obj.create_woo_schedule_activity(product_queue, "woo.product.data.queue.ept", True)
                continue
            self._cr.commit()
            if not product_queue_line_ids:
                continue

            product_queue_line_ids.process_woo_product_queue_lines()
            if time.time() - start > product_queue_process_cron_time - 60:
                return True
        return True

    def process_woo_product_queue_lines(self):
        """
        This method is used to process the queue lines from Webhook, manually from form view or after searching from
        auto process cron.
        @author: Maulik Barad on Date 27-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_template_obj = self.env['woo.product.template.ept']

        is_skip_products = self.queue_id.woo_skip_existing_products

        self.env.cr.execute(
            "update woo_product_data_queue_ept set is_process_queue = False where is_process_queue = True")
        self._cr.commit()
        woo_product_template_obj.sync_products(self, self.woo_instance_id, is_skip_products)
        return True

    def woo_image_import(self):
        """
        This method is used to import the product images explicitly.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 30 November 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_obj = self.env['woo.product.template.ept']
        product_dict = {}
        template_images_updated = False
        product_queue_lines = self.query_find_queue_line_for_import_image()
        for queue_line in product_queue_lines:
            browsable_queue_line = self.browse(queue_line)
            woo_template = woo_template_obj.search([('woo_tmpl_id', '=', browsable_queue_line.woo_synced_data_id),
                                                    ('woo_instance_id', '=', browsable_queue_line.woo_instance_id.id)],
                                                   limit=1)
            if not woo_template:
                continue
            product_data = json.loads(browsable_queue_line.woo_synced_data)
            woo_products = woo_template.woo_product_ids
            if woo_template.woo_product_type in ['simple', 'bundle']:
                woo_template_obj.update_product_images(product_data["images"], {}, woo_template, woo_products[0],
                                                       False)
            if woo_template.woo_product_type == 'variable':
                for variant_response in product_data.get('variations'):
                    woo_product = woo_products.filtered(lambda product: product.variant_id == str(
                        variant_response.get('id')) and product.woo_template_id == woo_template)
                    if not woo_product:
                        continue
                    if not woo_template.product_tmpl_id.image_1920:
                        product_dict.update({'product_tmpl_id': woo_template.product_tmpl_id, 'is_image': True})

                    woo_template_obj.update_product_images(product_data["images"], variant_response["image"],
                                                           woo_template, woo_product, template_images_updated,
                                                           product_dict)
                    template_images_updated = True
            self._cr.commit()
            browsable_queue_line.write({'image_import_state': 'done', 'woo_synced_data': False})
        return True

    def query_find_queue_line_for_import_image(self):
        """
        This method is used to search product queue lines which are remaining to import an image for the product.
        @return: product_queue_list
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 1 December 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        query = """select id from woo_product_data_queue_line_ept
                    where state='done' and image_import_state = 'pending'
                    ORDER BY create_date ASC limit 100"""
        self._cr.execute(query)
        product_queue_lines = self._cr.fetchall()
        return product_queue_lines

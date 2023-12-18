# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import logging

from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger("WooCommerce")


class WooProductDataQueueEpt(models.Model):
    _name = 'woo.product.data.queue.ept'
    _description = "WooCommerce Products Synced Queue Process"
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(copy=False)
    woo_skip_existing_products = fields.Boolean("Do not Update Existing Product")
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instances")
    state = fields.Selection([('draft', 'Draft'), ('partial', 'Partially Done'),
                              ("failed", "Failed"), ('done', 'Done')], default='draft',
                             compute="_compute_state", store=True, tracking=True)
    queue_line_ids = fields.One2many('woo.product.data.queue.line.ept', 'queue_id')
    common_log_lines_ids = fields.One2many("common.log.lines.ept", compute="_compute_log_lines")
    products_count = fields.Integer(compute='_compute_lines')
    product_draft_state_count = fields.Integer(compute='_compute_lines')
    product_done_state_count = fields.Integer(compute='_compute_lines')
    product_failed_state_count = fields.Integer(compute='_compute_lines')
    cancelled_line_count = fields.Integer(compute='_compute_lines')
    created_by = fields.Selection([("import", "By Import Process"), ("webhook", "By Webhook")], default="import",
                                  help="Identify the process that generated a queue.")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    is_action_require = fields.Boolean(default=False,
                                       help="it is used to find the action require queue")

    @api.depends("queue_line_ids.state")
    def _compute_lines(self):
        """
        Computes product queue lines by different states.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            queue_lines = record.queue_line_ids
            record.products_count = len(queue_lines)
            record.product_draft_state_count = len(queue_lines.filtered(lambda x: x.state == "draft"))
            record.product_done_state_count = len(queue_lines.filtered(lambda x: x.state == "done"))
            record.product_failed_state_count = len(queue_lines.filtered(lambda x: x.state == "failed"))
            record.cancelled_line_count = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("queue_line_ids.state")
    def _compute_state(self):
        """
        Computes state of Product queue from queue lines' state.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            if (record.product_done_state_count + record.cancelled_line_count) == record.products_count:
                record.state = "done"
            elif record.product_draft_state_count == record.products_count:
                record.state = "draft"
            elif record.product_failed_state_count == record.products_count:
                record.state = "failed"
            else:
                record.state = "partial"

    @api.depends("queue_line_ids.common_log_lines_ids")
    def _compute_log_lines(self):
        """
        Computes the log lines from the queue lines.
        @author: Maulik Barad on Date 05-Oct-2022.
        """
        for record in self:
            record.common_log_lines_ids = record.queue_line_ids.common_log_lines_ids

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherited and create a sequence and new product queue
        :param vals_list: It will contain the updated data and its type is Dictionary
        :return: It will return the object of newly created product queue
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_sequence_obj = self.env['ir.sequence']
        record_name = "/"
        sequence_id = self.env.ref("woo_commerce_ept.ir_sequence_product_data_queue").id
        for vals in vals_list:
            if sequence_id:
                record_name = ir_sequence_obj.browse(sequence_id).next_by_id()
            vals.update({"name": record_name})
        return super(WooProductDataQueueEpt, self).create(vals_list)

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        need_to_cancel_queue_lines = self.queue_line_ids.filtered(lambda x: x.state in ["draft", "failed"])
        need_to_cancel_queue_lines.write({"state": "cancel", 'image_import_state': 'done', 'woo_synced_data': False})
        return True

    def create_product_queue_from_webhook(self, product_data, instance, wc_api):
        """
        This method used to create a product queue from webhook response.
        @author: Haresh Mori on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        is_sync_image_with_product = 'done'
        product_data_queue_obj = self.env['woo.product.data.queue.ept']
        product_queue_line_obj = self.env['woo.product.data.queue.line.ept']
        process_import_export_obj = self.env["woo.process.import.export"]
        product_ept_obj = self.env["woo.product.template.ept"]

        if product_data.get("type") == "variable":
            variants_data = product_ept_obj.get_variations_from_woo(product_data, wc_api, instance)

            if isinstance(variants_data, list):
                product_data.update({"variations": variants_data})

        product_data_queue = product_data_queue_obj.search(
            [('woo_instance_id', '=', instance.id), ('created_by', '=', 'webhook'), ('state', '=', 'draft')], limit=1)

        if instance.sync_images_with_product:
            is_sync_image_with_product = 'pending'

        if product_data_queue:
            existing_product_queue_line_data = product_queue_line_obj.search(
                [('woo_instance_id', '=', instance.id), ('woo_synced_data_id', '=', product_data.get('id')),
                 ('state', 'in', ['draft', 'failed'])])
            if not existing_product_queue_line_data:
                sync_queue_vals_line = {
                    'woo_instance_id': instance.id, 'name': product_data.get('name'), 'synced_date': datetime.now(),
                    'queue_id': product_data_queue.id, 'woo_synced_data': json.dumps(product_data),
                    'woo_update_product_date': product_data.get('date_modified'),
                    'woo_synced_data_id': product_data.get('id'),
                    'image_import_state': is_sync_image_with_product
                }
                product_queue_line_obj.create(sync_queue_vals_line)
            else:
                existing_product_queue_line_data.write({'woo_synced_data': json.dumps(product_data)})
            _logger.info("Added product id : %s in existing product queue %s", product_data.get('id'),
                         product_data_queue.display_name)

        if product_data_queue and len(product_data_queue.queue_line_ids) >= 50:
            product_data_queue.queue_line_ids.process_woo_product_queue_lines()

        elif not product_data_queue:
            import_export = process_import_export_obj.create({"woo_instance_id": instance.id})
            import_export.sudo().woo_import_products([product_data], "webhook")
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='woo.product.data.queue.line.ept')

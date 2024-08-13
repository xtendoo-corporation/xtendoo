# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger("WooCommerce")


class WooCustomerDataQueueEpt(models.Model):
    _name = "woo.customer.data.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "WooCommerce Customer Data Queue"

    name = fields.Char()
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instance",
                                      help="Determines that queue line associated with particular instance")
    state = fields.Selection([('draft', 'Draft'), ('partial', 'Partial Done'),
                              ("failed", "Failed"), ('done', 'Done')],
                             default='draft', compute="_compute_state", store=True, tracking=True)
    queue_line_ids = fields.One2many('woo.customer.data.queue.line.ept', 'queue_id', readonly=1)
    customers_count = fields.Integer(string='Total Customers', compute='_compute_lines')
    draft_state_count = fields.Integer(string='Draft', compute='_compute_lines')
    done_state_count = fields.Integer(string='Done', compute='_compute_lines')
    failed_state_count = fields.Integer(string='Failed', compute='_compute_lines')
    cancelled_line_count = fields.Integer(compute='_compute_lines')
    common_log_lines_ids = fields.One2many("common.log.lines.ept", compute="_compute_log_lines")
    created_by = fields.Selection([("import", "By Import Process"), ("webhook", "By Webhook")], default="import",
                                  help="Identify the process that generated a queue.")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    is_action_require = fields.Boolean(default=False, help="it is used to find the action require queue")

    @api.depends("queue_line_ids.state")
    def _compute_lines(self):
        """
        Computes customer queue lines by different states.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            queue_lines = record.queue_line_ids
            record.customers_count = len(queue_lines)
            record.draft_state_count = len(queue_lines.filtered(lambda x: x.state == "draft"))
            record.done_state_count = len(queue_lines.filtered(lambda x: x.state == "done"))
            record.failed_state_count = len(queue_lines.filtered(lambda x: x.state == "failed"))
            record.cancelled_line_count = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("queue_line_ids.state")
    def _compute_state(self):
        """
        Computes state of Customer queue from queue lines' state.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            if (record.done_state_count + record.cancelled_line_count) == record.customers_count:
                record.state = "done"
            elif record.draft_state_count == record.customers_count:
                record.state = "draft"
            elif record.failed_state_count == record.customers_count:
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
        Inherited and create a sequence and new customer queue
        :param vals_list: It will contain the updated data and its type is Dictionary
        :return: It will return the object of newly created customer queue
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_sequence_obj = self.env['ir.sequence']
        record_name = "/"
        sequence_id = self.env.ref("woo_commerce_ept.woo_customer_data_queue_ept_sequence").id
        for vals in vals_list:
            if sequence_id:
                record_name = ir_sequence_obj.browse(sequence_id).next_by_id()
            vals.update({"name": record_name})
        return super(WooCustomerDataQueueEpt, self).create(vals_list)

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        need_to_cancel_queue_lines = self.queue_line_ids.filtered(lambda x: x.state in ["draft", "failed"])
        need_to_cancel_queue_lines.write({"state": "cancel"})
        return True

    def create_customer_data_queue_for_webhook(self, instance, customer):
        """
        @param customer: Customer's data from webhook.
        @param instance: Record of Woo Instance.
        @author: Maulik Barad on Date 27-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        customer_data_queue_line_obj = self.env['woo.customer.data.queue.line.ept']
        customer_queue = self.search([('woo_instance_id', '=', instance.id), ('created_by', '=', "webhook"),
                                      ('state', '=', 'draft')], limit=1)
        if customer_queue:
            message = "Customer %s added into Queue %s." % (customer.get("first_name"), customer_queue.name)
        else:
            customer_queue = self.create({'woo_instance_id': instance.id, "created_by": "webhook"})
            message = "Customer Queue %s created." % customer_queue.name
        _logger.info(message)
        existing_customer_data_queue_line = customer_data_queue_line_obj.search(
            [('woo_synced_data_id', '=', customer.get('id')), ('woo_instance_id', '=', instance.id),
             ('state', 'in', ['draft', 'failed'])])
        if not existing_customer_data_queue_line:
            sync_vals = {
                'woo_instance_id': instance.id,
                'queue_id': customer_queue.id,
                'woo_synced_data': json.dumps(customer),
                'woo_synced_data_id': customer.get('id'),
                'name': customer.get('billing').get('first_name') + " " + customer.get('billing').get(
                    'last_name') if customer.get('billing') else ''
            }
            customer_data_queue_line_obj.create(sync_vals)
        else:
            existing_customer_data_queue_line.write({'woo_synced_data': json.dumps(customer)})

        if len(customer_queue.queue_line_ids) >= 50:
            customer_queue.queue_line_ids.process_woo_customer_queue_lines()
        return customer_queue

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='woo.customer.data.queue.line.ept')

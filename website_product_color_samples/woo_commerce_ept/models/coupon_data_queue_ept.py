# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api

_logger = logging.getLogger("WooCommerce")


class WooCouponDataQueueEpt(models.Model):
    _name = "woo.coupon.data.queue.ept"
    _description = "WooCommerce Coupon Data Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instances")
    state = fields.Selection([('draft', 'Draft'), ('partial', 'Partially Done'), ("failed", "Failed"),
                              ('done', 'Done')], default='draft', compute="_compute_state", store=True, tracking=True)
    coupon_data_queue_line_ids = fields.One2many('woo.coupon.data.queue.line.ept', 'coupon_data_queue_id', readonly=1)
    common_log_lines_ids = fields.One2many("common.log.lines.ept", compute="_compute_log_lines")
    total_line_count = fields.Integer(compute="_compute_lines", help="Counts total queue lines.")
    draft_line_count = fields.Integer(compute="_compute_lines", help="Counts draft queue lines.")
    failed_line_count = fields.Integer(compute="_compute_lines", help="Counts failed queue lines.")
    done_line_count = fields.Integer(compute="_compute_lines", help="Counts done queue lines.")
    cancelled_line_count = fields.Integer(compute="_compute_lines", help="Counts cancelled queue lines.")
    created_by = fields.Selection([("import", "By Import Process"), ("webhook", "By Webhook")],
                                  help="Identify the process that generated a queue.", default="import")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")

    @api.depends("coupon_data_queue_line_ids.state")
    def _compute_lines(self):
        """
        Computes coupon queue lines by different states.
        @author: Nilesh Parmar on Date 28 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            queue_lines = record.coupon_data_queue_line_ids
            record.total_line_count = len(queue_lines)
            record.draft_line_count = len(queue_lines.filtered(lambda x: x.state == "draft"))
            record.failed_line_count = len(queue_lines.filtered(lambda x: x.state == "failed"))
            record.done_line_count = len(queue_lines.filtered(lambda x: x.state == "done"))
            record.cancelled_line_count = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("coupon_data_queue_line_ids.state")
    def _compute_state(self):
        """
        Computes state of coupon queue from queue lines' state.
        @author: Nilesh Parmar on Date 28 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            if (record.done_line_count + record.cancelled_line_count) == record.total_line_count:
                record.state = "done"
            elif record.draft_line_count == record.total_line_count:
                record.state = "draft"
            elif record.failed_line_count == record.total_line_count:
                record.state = "failed"
            elif record.failed_line_count > 0 or record.draft_line_count > 0:
                record.state = "partial"

    @api.depends("coupon_data_queue_line_ids.common_log_lines_ids")
    def _compute_log_lines(self):
        """
        Computes the log lines from the queue lines.
        @author: Maulik Barad on Date 05-Oct-2022.
        """
        for record in self:
            record.common_log_lines_ids = record.coupon_data_queue_line_ids.common_log_lines_ids

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherited Method for giving sequence to ICT.
        @param vals_list: Dictionary of values.
        @return: New created record.
        @author: Nilesh Parmar on Date 28 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_sequence_obj = self.env['ir.sequence']
        record_name = "/"
        sequence_id = self.env.ref("woo_commerce_ept.ir_sequence_coupon_data_queue").id
        for vals in vals_list:
            if sequence_id:
                record_name = ir_sequence_obj.browse(sequence_id).next_by_id()
            vals.update({"name": record_name})
        return super(WooCouponDataQueueEpt, self).create(vals_list)

    def create_woo_data_queue_lines(self, coupons):
        """
        Creates queue lines from imported JSON data of Coupons.
        @param coupons: coupons in JSON format.
        @author: Nilesh Parmar on Date 28 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals_list = []
        for coupon in coupons:
            coupon_data_queue_line_obj = self.env["woo.coupon.data.queue.line.ept"]
            coupon_queue_line_id = coupon_data_queue_line_obj.search(
                [('woo_coupon', '=', coupon["id"]), ('state', 'in', ['draft', 'failed'])], limit=1)
            if coupon_queue_line_id:
                coupon_queue_line_id.update({'coupon_data': coupon})
            else:
                vals_list = {"coupon_data_queue_id": self.id,
                                  "woo_coupon": coupon["id"],
                                  "coupon_data": coupon,
                                  "number": coupon["code"]}
                if vals_list:
                    coupon_data_queue_line_obj.create(vals_list)
        return False

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        @author: Nilesh Parmar on Date 28 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        need_to_cancel_queue_lines = self.coupon_data_queue_line_ids.filtered(lambda x: x.state in ["draft", "failed"])
        need_to_cancel_queue_lines.write({"state": "cancel"})
        return True

    def create_coupon_queue_from_webhook(self, result, instance):
        """"
        This method used to create a coupon queue from the coupon webhook response and also
        process the queue line.
        @author: Haresh Mori on Date 2-Jan-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_coupon_obj = self.env["woo.coupons.ept"]
        coupon_data_queue_obj = self.env["woo.coupon.data.queue.ept"]
        coupon_data_queue = coupon_data_queue_obj.search(
            [('woo_instance_id', '=', instance.id), ('created_by', '=', 'webhook'), ('state', '=', 'draft')], limit=1)

        if coupon_data_queue:
            coupon_data_queue.create_woo_data_queue_lines([result])
            _logger.info("Added coupon id : %s in existing queue %s", result.get('id'),
                         coupon_data_queue.display_name)
            if len(coupon_data_queue.coupon_data_queue_line_ids) >= 50:
                coupon_data_queue.coupon_data_queue_line_ids.process_coupon_queue_line()

        elif not coupon_data_queue:
            woo_coupon_obj.create_woo_coupon_data_queue(instance, [result], created_by="webhook")
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='woo.coupon.data.queue.line.ept')

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WooOrderDataQueueEpt(models.Model):
    """
    Model for storing imported order data and creating sale orders that data.
    @author: Maulik Barad on Date 24-Oct-2019.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """
    _name = "woo.order.data.queue.ept"
    _description = "WooCommerce Order Data Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(help="Sequential name of imported order.", copy=False)
    instance_id = fields.Many2one("woo.instance.ept", copy=False,
                                  help="Order imported from this Woocommerce Instance.")
    state = fields.Selection([("draft", "Draft"), ("partial", "Partially Done"),
                              ("failed", "Failed"), ("done", "Done")], copy=False, default="draft",
                             compute="_compute_state", tracking=True, store=True)
    order_data_queue_line_ids = fields.One2many("woo.order.data.queue.line.ept", "order_data_queue_id")
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
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    is_action_require = fields.Boolean(default=False, help="it is used to find the action require queue")
    queue_type = fields.Selection([("unshipped", "Unshipped"), ("shipped", "Shipped")], default="unshipped", copy=False,
                                  help="Type of queue as per the order's data.")

    @api.depends("order_data_queue_line_ids.state")
    def _compute_lines(self):
        """
        Computes order queue lines by different states.
        @author: Maulik Barad on Date 07-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            queue_lines = record.order_data_queue_line_ids
            record.total_line_count = len(queue_lines)
            record.draft_line_count = len(queue_lines.filtered(lambda x: x.state == "draft"))
            record.failed_line_count = len(queue_lines.filtered(lambda x: x.state == "failed"))
            record.done_line_count = len(queue_lines.filtered(lambda x: x.state == "done"))
            record.cancelled_line_count = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("order_data_queue_line_ids.state")
    def _compute_state(self):
        """
        Computes state of Order queue from different states of lines.
        @author: Maulik Barad on Date 07-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            if (record.done_line_count + record.cancelled_line_count) == record.total_line_count:
                record.state = "done"
            elif record.draft_line_count == record.total_line_count:
                record.state = "draft"
            elif record.failed_line_count == record.total_line_count:
                record.state = "failed"
            else:
                record.state = "partial"

    @api.depends("order_data_queue_line_ids.common_log_lines_ids")
    def _compute_log_lines(self):
        """
        Computes the log lines from the queue lines.
        @author: Maulik Barad on Date 05-Oct-2022.
        """
        for record in self:
            record.common_log_lines_ids = record.order_data_queue_line_ids.common_log_lines_ids

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherited Method for giving sequence to ICT.
        @author: Maulik Barad on Date 26-Sep-2019.
        @param vals_list: Dictionary of values.
        @return: New created record.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_sequence_obj = self.env['ir.sequence']
        sequence_id = self.env.ref("woo_commerce_ept.ir_sequence_order_data_queue").id
        for vals in vals_list:
            record_name = vals.get("name")
            if sequence_id and not record_name:
                record_name = ir_sequence_obj.browse(sequence_id).next_by_id()
            vals.update({"name": record_name})
        return super(WooOrderDataQueueEpt, self).create(vals_list)

    def create_woo_data_queue_lines(self, orders):
        """
        Creates queue lines from imported JSON data of orders.
        @author: Maulik Barad on Date 04-Nov-2019.
        @param orders: Orders in JSON format.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals_list = []
        woo_order_data_queue_line_obj = self.env["woo.order.data.queue.line.ept"]
        for order in orders:
            existing_order_data_queue_line = woo_order_data_queue_line_obj.search(
                [('woo_order', '=', order["id"]), ('instance_id', '=', self.instance_id.id),
                 ('state', 'in', ['draft', 'failed'])])
            if existing_order_data_queue_line:
                existing_order_data_queue_line.write({'order_data': order})
            else:
                vals_list.append({"order_data_queue_id": self.id,
                                  "woo_order": order["id"],
                                  "order_data": order,
                                  "number": order["number"],
                                  })
        if vals_list:
            return woo_order_data_queue_line_obj.create(vals_list)
        return False

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        @author: Maulik Barad on Date 25-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        need_to_cancel_queue_lines = self.order_data_queue_line_ids.filtered(lambda x: x.state in ["draft", "failed"])
        need_to_cancel_queue_lines.write({"state": "cancel"})
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='woo.order.data.queue.line.ept')

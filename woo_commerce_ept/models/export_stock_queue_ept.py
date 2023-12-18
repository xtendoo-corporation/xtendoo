# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger("Woo Commerce Export Stock Queue")


class WooExportStockQueueEpt(models.Model):
    """
    Model for exporting stock to Woo via the queue structure.
    @author: Maulik Barad on Date 05-Oct-2022.
    """
    _name = "woo.export.stock.queue.ept"
    _description = "WooCommerce Export Stock Queue"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(help="Sequential name of queue.", copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", copy=False,
                                      help="Export stock to this Woocommerce Instance.")
    state = fields.Selection([("draft", "Draft"), ("partial", "Partially Done"),
                              ("failed", "Failed"), ("done", "Done")], copy=False, default="draft",
                             compute="_compute_state", tracking=True, store=True)
    export_stock_queue_line_ids = fields.One2many("woo.export.stock.queue.line.ept", "export_stock_queue_id")
    common_log_lines_ids = fields.One2many("common.log.lines.ept", compute="_compute_log_lines")
    queue_line_total_records = fields.Integer(compute="_compute_lines", help="Counts total queue lines.")
    queue_line_draft_records = fields.Integer(compute="_compute_lines", help="Counts draft queue lines.")
    queue_line_fail_records = fields.Integer(compute="_compute_lines", help="Counts failed queue lines.")
    queue_line_done_records = fields.Integer(compute="_compute_lines", help="Counts done queue lines.")
    queue_line_cancel_records = fields.Integer(compute="_compute_lines", help="Counts cancelled queue lines.")
    is_process_queue = fields.Boolean("Is Processing Queue", default=False)
    running_status = fields.Char(default="Running...")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    is_action_require = fields.Boolean(default=False, help="it is used to find the action require queue")

    @api.depends("export_stock_queue_line_ids.state")
    def _compute_lines(self):
        """
        Computes order queue lines by different states.
        @author: Maulik Barad on Date 07-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            queue_lines = record.export_stock_queue_line_ids
            record.queue_line_total_records = len(queue_lines)
            record.queue_line_draft_records = len(queue_lines.filtered(lambda x: x.state == "draft"))
            record.queue_line_fail_records = len(queue_lines.filtered(lambda x: x.state == "failed"))
            record.queue_line_done_records = len(queue_lines.filtered(lambda x: x.state == "done"))
            record.queue_line_cancel_records = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("export_stock_queue_line_ids.common_log_lines_ids")
    def _compute_log_lines(self):
        """
        Computes the log lines from the queue lines.
        @author: Maulik Barad on Date 05-Oct-2022.
        """
        for record in self:
            record.common_log_lines_ids = record.export_stock_queue_line_ids.common_log_lines_ids

    @api.depends("export_stock_queue_line_ids.state")
    def _compute_state(self):
        """
        Computes state of Order queue from different states of lines.
        @author: Maulik Barad on Date 07-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            if (record.queue_line_done_records + record.queue_line_cancel_records) == record.queue_line_total_records:
                record.state = "done"
            elif record.queue_line_draft_records == record.queue_line_total_records:
                record.state = "draft"
            elif record.queue_line_fail_records == record.queue_line_total_records:
                record.state = "failed"
            else:
                record.state = "partial"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherited Method for giving sequence to export stock queue.
        @author: Maulik Barad on Date 26-Sep-2019.
        """
        ir_sequence_obj = self.env["ir.sequence"]
        sequence_id = self.env.ref("woo_commerce_ept.ir_sequence_export_stock_data_queue").id
        sequence = ir_sequence_obj.browse(sequence_id)

        for vals in vals_list:
            record_name = vals.get("name")
            if sequence_id and not record_name:
                record_name = sequence.next_by_id()
            vals.update({"name": record_name})

        return super(WooExportStockQueueEpt, self).create(vals_list)

    def create_woo_export_stock_queue(self, woo_instance, stock_data):
        """
        Creates export stock queue from the stock data.
        @param stock_data:
        @param woo_instance: Instance of Woocommerce.
        @author: Maulik Barad on Date 05-Oct-2019.
        """
        queues_list = self
        bus_bus_obj = self.env["bus.bus"]
        while stock_data:
            data = stock_data[:50]
            if data:
                stock_queue = self.create({"woo_instance_id": woo_instance.id})
                queues_list += stock_queue
                _logger.info("Export stock queue %s created.", stock_queue.name)

                stock_queue.create_queue_lines(data)
                _logger.info("Lines added in stock queue %s.", stock_queue.name)

                del stock_data[:50]
                message = "Export Stock Queue created %s" % stock_queue.name
                bus_bus_obj._sendone(self.env.user.partner_id, "simple_notification",
                                     {"title": _("WooCommerce Connector"), "message": _(message), "sticky": False,
                                      "warning": True})
                self._cr.commit()

        return queues_list

    def create_queue_lines(self, stock_data):
        """
        Creates queue lines from imported JSON data of orders.
        @author: Maulik Barad on Date 04-Nov-2019.
        @param stock_data:
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals_list = []
        queue_line_obj = self.env["woo.export.stock.queue.line.ept"]
        for data in stock_data:
            vals_list.append({
                "batch_details": data.get("batch_details"),
                "woo_tmpl_id": data.get("woo_tmpl_id"),
                "product_type": data.get("product_type"),
                "export_stock_queue_id": self.id
            })
        if vals_list:
            return queue_line_obj.create(vals_list)
        return False

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env["queue.line.dashboard"]
        return dashboard.get_data(table="woo.export.stock.queue.line.ept")

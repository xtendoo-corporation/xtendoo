#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import models, api, _


class EbayQueueProcessEpt(models.TransientModel):
    """
    Describes Wizard for processing order queue
    """
    _name = 'ebay.queue.process.ept'
    _description = 'Ebay Queue Process Ept'

    def manual_queue_process(self):
        """
        This method is use to process manually the queue line data of order and product.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 15 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "process_order_queue_manually":
            self.process_order_queue_manually()
        if queue_process == "process_product_queue_manually":
            self.process_product_queue_manually()

    @api.model
    def process_order_queue_manually(self):
        """
        This method is use to process the order data queues manually.
        """
        ebay_order_queue_line_obj = self.env["ebay.order.data.queue.line.ept"]
        order_queue_ids = self._context.get('active_ids')
        order_queue_cron = self.env.ref("ebay_ept.ir_cron_child_to_process_order_queue")
        self.check_running_cron_scheduler(order_queue_cron)
        for order_queue_id in order_queue_ids:
            order_queue_lines = ebay_order_queue_line_obj.search(
                [("ebay_order_data_queue_id", "=", order_queue_id), ("state", "in", ('draft', 'failed'))])
            order_queue_lines.process_import_order_queue_data()
        return True

    @api.model
    def process_product_queue_manually(self):
        """
        This method is use to create product from the queue line.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 15 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        import_product_queue_line_obj = self.env["ebay.import.product.queue.line"]
        product_queue_ids = self._context.get('active_ids')
        product_queue_cron = self.env.ref("ebay_ept.ir_cron_child_to_process_product_queue")
        self.check_running_cron_scheduler(product_queue_cron)
        for product_queue_id in product_queue_ids:
            product_queue_lines = import_product_queue_line_obj.search([
                ("sync_import_product_queue_id", "=", product_queue_id),
                ("state", "in", ('draft', 'failed'))
            ])
            product_queue_lines.process_import_product_queue_data()
        return True

    @staticmethod
    def check_running_cron_scheduler(cron_record):
        """
        This method is use to check if Queue cron is active, then user can not process manually
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        if cron_record and cron_record.active:
            child_cron = cron_record.try_cron_lock()
            # if child_cron and child_cron.get('result'):
            #     message = "This process executed using scheduler, " \
            #               "Next Scheduler execute for this process will " \
            #               "run in %s Minutes" % child_cron.get('result')
            #     raise UserError(_(message))
            if child_cron and child_cron.get('reason'):
                raise UserError(_(child_cron.get('reason')))

    def set_to_completed_queue(self):
        """
        This method is used to change the queue state as completed.
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "set_to_completed_order_queue":
            self.set_to_completed_order_queue_manually()
        if queue_process == "set_to_completed_product_queue":
            self.set_to_completed_product_queue_manually()

    def set_to_completed_order_queue_manually(self):
        """
        This method is used to set order queue as completed. You can call the method from here:
        Magento => Logs => Orders => SET TO COMPLETED
        :return:
        """
        order_queue_ids = self._context.get('active_ids')
        order_queue_ids = self.env['ebay.order.data.queue.ept'].browse(order_queue_ids)
        order_queue_cron = self.env.ref(
            "ebay_ept.ir_cron_child_to_process_order_queue"
        )
        self.check_running_cron_scheduler(order_queue_cron)
        for order_queue_id in order_queue_ids:
            queue_lines = order_queue_id.order_data_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            order_queue_id.message_post(
                body=_("Manually set to cancel queue lines - %s ") % (queue_lines.mapped('ebay_order_id')))
        return True

    def set_to_completed_product_queue_manually(self):
        """
        This method is used to set product queue as completed. You can call the method from here:
        Magento => Logs => Products => SET TO COMPLETED
        :return: True
        """
        product_queue_ids = self._context.get('active_ids')
        product_queue_ids = self.env['ebay.import.product.queue'].browse(product_queue_ids)
        product_queue_cron = self.env.ref(
            "ebay_ept.ir_cron_child_to_process_product_queue"
        )
        self.check_running_cron_scheduler(product_queue_cron)
        for product_queue_id in product_queue_ids:
            queue_lines = product_queue_id.import_product_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            product_queue_id.message_post(
                body=_("Manually set to cancel queue lines - %s ") % (queue_lines.mapped('ebay_item_id')))
        return True

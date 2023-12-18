# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import json
import logging
import time

from datetime import datetime

from odoo import models, fields

_logger = logging.getLogger("WooCommerce")


class WooCustomerDataQueueLineEpt(models.Model):
    _name = "woo.customer.data.queue.line.ept"
    _description = 'WooCommerce Customer Data Queue Line'
    _rec_name = "woo_synced_data_id"

    woo_instance_id = fields.Many2one('woo.instance.ept', string='Instance',
                                      help="Determines that queue line associated with particular instance")
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ("cancel", "Cancelled"), ('done', 'Done')],
                             default='draft')
    last_process_date = fields.Datetime(readonly=True)
    woo_synced_data = fields.Char(string='WooCommerce Synced Data')
    woo_synced_data_id = fields.Char(string='Woo Customer Id')
    queue_id = fields.Many2one('woo.customer.data.queue.ept', ondelete="cascade")
    common_log_lines_ids = fields.One2many("common.log.lines.ept", "woo_customer_data_queue_line_id",
                                           help="Log lines created against which line.")
    name = fields.Char(string="Customer", help="Customer Name of Woo Commerce")

    def process_woo_customer_queue_lines(self):
        """
        This method process the queue lines and creates partner and addresses.
        @author: Maulik Barad on Date 11-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        partner_obj = self.env['res.partner']
        common_log_line_obj = self.env["common.log.lines.ept"]

        commit_count = 0
        parent_partner = False

        for customer_queue_line in self:
            commit_count += 1
            if commit_count == 50:
                customer_queue_line.queue_id.is_process_queue = True
                self._cr.commit()
                commit_count = 0

            instance = customer_queue_line.woo_instance_id
            customer_val = json.loads(customer_queue_line.woo_synced_data)
            _logger.info("Start processing Woo customer Id %s for instance %s.", customer_val.get('id', False),
                         instance.name)

            if customer_val:
                parent_partner = partner_obj.woo_create_contact_customer(customer_val, instance)
            if parent_partner:
                partner_obj.woo_create_or_update_customer(customer_val.get('billing'), instance,
                                                          parent_partner, 'invoice')
                partner_obj.woo_create_or_update_customer(customer_val.get('shipping'), instance, parent_partner,
                                                          'delivery')
                customer_queue_line.write(
                    {'state': 'done', 'last_process_date': datetime.now(), 'woo_synced_data': False})
                # WooCommerce Meta Mapping for import Customers
                woo_operation = 'import_customer'
                if instance.meta_mapping_ids.filtered(lambda meta: meta.woo_operation == woo_operation):
                    instance.with_context(woo_operation=woo_operation).meta_field_mapping(customer_val, "import",
                                                                                          parent_partner)
            else:
                customer_queue_line.write({'state': 'failed', 'last_process_date': datetime.now()})
                common_log_line_obj.create_common_log_line_ept(
                    operation_type="import", module="woocommerce_ept", woo_instance_id=instance.id,
                    model_name=self._name, message="Please check customer name or addresses in WooCommerce.",
                    woo_customer_data_queue_line_id=customer_queue_line.id)
            customer_queue_line.queue_id.is_process_queue = False
            _logger.info("End processing Woo customer Id %s for instance %s.", customer_val.get('id', False),
                         instance.name)
        return True

    def woo_customer_data_queue_to_odoo(self):
        """
        This method used to call child methods of sync customer in odoo from queue line response.
        @param : self
        @return: True
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29 August 2020 .
        Task_id: 165956
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        customer_queue_ids = []
        woo_customer_data_queue_obj = self.env["woo.customer.data.queue.ept"]
        common_log_line_obj = self.env["common.log.lines.ept"]
        start = time.time()

        self.env.cr.execute(
            """update woo_customer_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        query = """select queue.id from woo_customer_data_queue_line_ept as queue_line
                    inner join woo_customer_data_queue_ept as queue on queue_line.queue_id = queue.id
                    where queue_line.state='draft' and queue.is_action_require = 'False'
                    ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        customer_queue_list = self._cr.fetchall()

        for result in customer_queue_list:
            customer_queue_ids.append(result[0])

        if not customer_queue_ids:
            return False
        customer_queues = woo_customer_data_queue_obj.browse(list(set(customer_queue_ids)))

        customer_queue_process_cron_time = customer_queues.woo_instance_id.get_woo_cron_execution_time(
            "woo_commerce_ept.process_woo_customer_data")
        for customer_queue in customer_queues:
            customer_queue.queue_process_count += 1
            if customer_queue.queue_process_count > 3:
                customer_queue.is_action_require = True
                note = "<p>Attention %s queue is processed 3 times you need to process it manually.</p>" % (
                    customer_queue.name)
                customer_queue.message_post(body=note)
                if customer_queue.woo_instance_id.is_create_schedule_activity:
                    common_log_line_obj.create_woo_schedule_activity(customer_queue, "woo.customer.data.queue.ept",
                                                                     True)
                continue
            queue_lines = customer_queue.queue_line_ids.filtered(lambda x: x.state == "draft")
            self._cr.commit()
            if not queue_lines:
                continue

            queue_lines.process_woo_customer_queue_lines()
            if time.time() - start > customer_queue_process_cron_time - 60:
                return True
        return True

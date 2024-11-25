import ast
import time
import logging
import pytz
from odoo.exceptions import UserError
from odoo import models, fields, _

utc = pytz.utc

_logger = logging.getLogger("Woo Commerce Export Stock Queue Line")


class WooOrderDataQueueLineEpt(models.Model):
    _name = "woo.export.stock.queue.line.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "WooCommerce Export Stock Queue Line"

    woo_instance_id = fields.Many2one(related="export_stock_queue_id.woo_instance_id", copy=False)
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"),
                              ("cancel", "Cancelled"), ("done", "Done")], default="draft", copy=False)
    product_type = fields.Selection([('simple', 'Simple'), ('variable', 'Variable')])
    export_stock_queue_id = fields.Many2one("woo.export.stock.queue.ept", required=True, ondelete="cascade", copy=False)
    common_log_lines_ids = fields.One2many("common.log.lines.ept", "woo_export_stock_queue_line_id",
                                           help="Log lines created against which line.")

    woo_tmpl_id = fields.Char()
    batch_details = fields.Char()
    last_process_date = fields.Datetime()
    quantity = fields.Integer()
    woocommerce_product_id = fields.Many2one('woo.product.product.ept', string="Product")
    name = fields.Char()

    def auto_export_stock_queue_lines_process(self):
        """
        This method is used to find export stock queue which queue lines have state in
        draft and is_action_require is False.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        export_stock_queue_obj = self.env["woo.export.stock.queue.ept"]
        export_stock_queue_ids = []
        qry = """UPDATE woo_export_stock_queue_ept SET is_process_queue = %s WHERE is_process_queue = %s"""
        self.env.cr.execute(qry, (False, True))
        self._cr.commit()

        query = """select distinct queue.id
                from woo_export_stock_queue_line_ept as queue_line  
                inner join woo_export_stock_queue_ept as queue on queue_line.export_stock_queue_id = queue.id
                where queue_line.state in (%s) and queue.is_action_require = %s
                GROUP BY queue.id
                ORDER BY queue.id ASC"""
        self.env.cr.execute(query, ('draft', 'False'))
        export_stock_queue_list = self._cr.fetchall()
        if not export_stock_queue_list:
            return True

        export_stock_queue_ids = [result[0] for result in export_stock_queue_list]

        queues = export_stock_queue_obj.browse(export_stock_queue_ids)
        self.export_stock_queue_manual_process_check(queues)
        return True

    def export_stock_queue_manual_process_check(self, queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the export stock queue line.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        start = time.time()
        export_stock_queue_process_cron_time = queues.woo_instance_id.get_woo_cron_execution_time(
            "woo_commerce_ept.process_woo_export_stock_queue")

        for queue in queues:
            export_stock_queue_line_ids = queue.export_stock_queue_line_ids.filtered(lambda x: x.state == "draft")

            if export_stock_queue_line_ids:
                queue.queue_process_count += 1
                if queue.queue_process_count > 3:
                    queue.is_action_require = True
                    note = "<p>Need to process this export stock queue manually.There are 3 attempts been made by " \
                           "automated action to process this queue,<br/>- Ignore, " \
                           "if this queue is already processed.</p>"
                    queue.message_post(body=note)
                    if queue.woo_instance_id.is_create_schedule_activity:
                        common_log_line_obj.create_woo_schedule_activity(queue, "woo.export.stock.queue.ept", True)
                    continue

                self._cr.commit()
                export_stock_queue_line_ids.process_export_stock_queue_data()
            if time.time() - start > export_stock_queue_process_cron_time - 60:
                return True
        return True

    def process_export_stock_queue_data(self):
        """
        This method is used to processes export stock queue lines.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        queue_id = self.export_stock_queue_id if len(self.export_stock_queue_id) == 1 else False

        if queue_id:
            instance = queue_id.woo_instance_id
            qry = """UPDATE woo_export_stock_queue_ept SET is_process_queue = %s WHERE is_process_queue = %s"""
            self.env.cr.execute(qry, (False, True))
            self._cr.commit()
            wc_api = instance.woo_connect()
            product_to_archive = []
            for queue_line in self:
                _logger.info('Starting Batch Export Stock Process.')
                batch_details = ast.literal_eval(queue_line.batch_details)
                try:
                    if queue_line.product_type == 'simple':
                        res = wc_api.post('products/batch', {'update': batch_details})
                    if queue_line.product_type == 'variable':
                        for batch in batch_details:
                            res = wc_api.post('products/%s/variations/batch' % queue_line.woo_tmpl_id,
                                              {'update': batch})
                    if res.status_code == 200:
                        queue_id.is_process_queue = True
                        queue_id.running_status = ''
                        queue_line.write({"state": "done", "batch_details": False})
                    else:
                        queue_line.write({"state": "failed"})
                except Exception as error:
                    raise UserError(
                        _("Something went wrong while Exporting Stock.\n\nPlease Check your Connection and Instance "
                          "Configuration.\n\n" + str(error)))
                _logger.info('Completed Product Batch Export Stock with [Status: %s]',
                             res.status_code)
                response = self.env["woo.product.template.ept"].check_woocommerce_response(
                    res, "Export Stock", "woo.export.stock.queue.ept", instance, stock_queue_line=queue_line.id)
                if not isinstance(response, dict):
                    continue

                if response.get('data', {}) and response.get('data', {}).get('status') != 200:
                    message = "Export Product Stock \n%s" % (response.get('message'))
                    common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                                   woo_instance_id=instance.id, message=message,
                                                                   model_name="woo.export.stock.queue.ept",
                                                                   woo_export_stock_queue_line_id=queue_line.id)
                    continue
            self._cr.commit()
            product_to_archive.extend(self.find_deleted_product_in_woo(response.get('update')))
        self.env["woo.product.template.ept"].archive_deleted_product(product_to_archive)
        if queue_id.common_log_lines_ids and queue_id.woo_instance_id.is_create_schedule_activity:
            common_log_line_obj.create_woo_schedule_activity()

        return True

    def find_deleted_product_in_woo(self,response_data):
        """
            This Method is used to find the deleted product or invalid_id product from woo store
            @param response_data: respose data received from woo store.
             :return: List
            @author: Gopal Chouhan @Emipro Technologies Pvt. Ltd on date 02-07-2024.
        """
        woo_deleted_products = []
        deleted_product_dict = list(filter(lambda prd: prd.get('error'), response_data))
        for prd in deleted_product_dict:
            if prd.get('error').get('message') == 'Invalid ID.' and prd.get('error').get('data').get('status') != 200:
                woo_deleted_products.append(prd.get('id'))
        return woo_deleted_products

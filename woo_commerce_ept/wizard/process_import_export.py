# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import csv
import json
import logging
import time
import os
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import pytz
import xlrd

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons.web_editor.tools import get_video_embed_code
from odoo.tools.misc import split_every

_logger = logging.getLogger("WooCommerce")


class WooProcessImportExport(models.TransientModel):
    _name = 'woo.process.import.export'
    _description = "WooCommerce Import/Export Process"

    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", domain=[("active", "=", True)])
    woo_operation = fields.Selection([
        ('import_product', 'Import Products'),
        ("import_specific_products", "Import Specific Product(s)"),
        ('import_customer', 'Import Customers'),
        ('import_unshipped_orders', 'Import Unshipped Orders'),
        ('import_completed_orders', 'Import Shipped Orders'),
        ('import_cancel_orders', 'Import Cancel Orders'),
        ("import_specific_orders", "Import Specific Order(s)"),
        ('is_update_order_status', "Export Shippment Infomation / Update Order Status"),
        ('import_product_tags', 'Import Tags'),
        ('import_attribute', 'Import Attributes'),
        ('import_category', 'Import Categories'),
        ('import_coupon', 'Import Coupons'),
        ('import_stock', 'Import Stock'),
        ('export_stock', 'Export Stock'),
        ("update_tags", "Update Tags"),
        ("export_tags", "Export Tags"),
        ('update_category', 'Update Categories'),
        ('export_category', 'Export Categories'),
        ('update_coupon', 'Update Coupons'),
        ('export_coupon', 'Export Coupons'),
        ('import_product_from_csv', 'Map Products')
    ], string="Operation")
    woo_skip_existing_product = fields.Boolean(string="Do not update existing products",
                                               help="Check if you want to skip existing products in odoo",
                                               default=False)
    orders_before_date = fields.Datetime("To")
    orders_after_date = fields.Datetime("From")
    woo_is_set_price = fields.Boolean(string="Woo Set Price ?")
    woo_is_set_stock = fields.Boolean(string="Woo Set Stock ?")
    woo_publish = fields.Selection([('publish', 'Publish'), ('unpublish', 'Unpublish')], string="Publish In Website ?",
                                   help="If select publish then Publish the product in website and If the select "
                                        "unpublish then Unpublish the product from website")
    woo_is_set_image = fields.Boolean(string="Woo Set Image ?", default=False)
    woo_basic_detail = fields.Boolean(string="Basic Detail", default=True)
    export_stock_from = fields.Datetime(help="It is used for exporting stock from Odoo to Woo.")
    import_products_method = fields.Selection([("import_all", "Import all"),
                                               ("new_and_updated", "New and Updated Only")],
                                              "Products to Import", default="new_and_updated")
    choose_file = fields.Binary(help="Select CSV file to upload.")
    file_name = fields.Char(help="Name of CSV file.")
    csv_data = fields.Binary('CSV File', readonly=True, attachment=False)
    cron_process_notification = fields.Text(string="Note: ", store=False,
                                            help="Used to display that cron will be run after some time")
    is_hide_execute_button = fields.Boolean(default=False, store=False, help="Used to hide the execute button from "
                                                                             "opration wizard while seleted opration "
                                                                             "cron is running in backend")
    auto_apply_adjustments = fields.Boolean(default=False, help="If it is set, the quants will be applied "
                                                                "automatically while importing stock.")
    products_after_date = fields.Datetime("From Date")
    products_before_date = fields.Datetime("To Date")
    woo_video_url = fields.Char('Video URL',
                                help='URL of a video for showcasing by operations.')
    woo_video_embed_code = fields.Html(compute="_compute_woo_video_embed_code", sanitize=False)
    woo_template_ids = fields.Text(string="Template Ids",
                                   help="Based on template ids get product from woo commerce and import in odoo")
    woo_order_ids = fields.Text(string="Order Ids",
                                help="Based on template ids get product from woo commerce and import products in odoo")

    @api.depends('woo_video_url')
    def _compute_woo_video_embed_code(self):
        for image in self:
            image.woo_video_embed_code = get_video_embed_code(image.woo_video_url)

    @api.constrains('orders_after_date', 'orders_before_date', 'products_after_date', 'products_before_date')
    def _check_order_after_before_date(self):
        """
        Constraint for from and to date of import order process.
        @author: Maulik Barad on Date 08-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_operation in ['import_unshipped_orders',
                                  'import_completed_orders'] and self.orders_before_date <= self.orders_after_date:
            raise UserError(_("From date should be less than To date.\nPlease enter proper date range for import "
                              "order process."))
        elif self.woo_operation == 'import_product' and self.products_before_date <= self.products_after_date:
            raise UserError(_("From date should be less than To date.\nPlease enter proper date range for import "
                              "products process."))

    @api.onchange('woo_operation')
    def _onchange_woo_operation(self):
        """
        Onchange method of Instance as need to set the From date for import order process.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 September 2020 .
        Task_id: 165893
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        self.cron_process_notification = False
        self.is_hide_execute_button = False
        from_date = fields.Datetime.now() - timedelta(days=1)
        if self.woo_instance_id:
            # Attach WooCommerce Operations Videos
            self.set_video_based_on_operation()

            if self.woo_instance_id.last_order_import_date and self.woo_operation == 'import_unshipped_orders':
                self.orders_after_date = self.woo_instance_id.last_order_import_date
            elif self.woo_instance_id.last_completed_order_import_date and \
                    self.woo_operation == 'import_completed_orders':
                self.orders_after_date = self.woo_instance_id.last_completed_order_import_date
            elif self.woo_instance_id.last_cancel_order_import_date and \
                    self.woo_operation == 'import_cancel_orders':
                self.orders_after_date = self.woo_instance_id.last_cancel_order_import_date - timedelta(days=7)
            else:
                self.orders_after_date = from_date
            if self.woo_instance_id.last_inventory_update_time:
                self.export_stock_from = self.woo_instance_id.last_inventory_update_time
            else:
                self.export_stock_from = fields.Datetime.now() - timedelta(days=30)
            if self.woo_instance_id.import_products_last_date and self.woo_operation == 'import_product':
                self.products_after_date = self.woo_instance_id.import_products_last_date
            else:
                self.products_after_date = from_date
        else:
            self.orders_after_date = from_date
            self.products_after_date = from_date
        if self.woo_operation == 'import_unshipped_orders':
            self.woo_check_running_schedulers('ir_cron_woo_import_order_instance_')
        if self.woo_operation == 'import_completed_orders':
            self.woo_check_running_schedulers('ir_cron_woo_import_complete_order_instance_')
        elif self.woo_operation == "import_cancel_orders":
            self.woo_check_running_schedulers('ir_cron_woo_import_cancel_order_instance_')
        if self.woo_operation == 'is_update_order_status':
            self.woo_check_running_schedulers('ir_cron_woo_update_order_status_instance_')
        if self.woo_operation == 'export_stock':
            self.woo_check_running_schedulers('ir_cron_update_woo_stock_instance_')
        self.orders_before_date = fields.Datetime.now()

    def execute(self):
        """
        This method is used to perform the selected operation.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        queues = False
        actions = {"import_customer": ["woo_commerce_ept.woo_customer_data_queue_ept_action",
                                       "woo_commerce_ept.woo_customer_data_data_queue_ept_form_view"],
                   "import_product": ["woo_commerce_ept.action_woo_product_data_queue_ept",
                                      "woo_commerce_ept.woo_product_data_queue_form_view_ept"],
                   "import_unshipped_orders": ["woo_commerce_ept.action_woo_unshipped_order_queue_ept",
                                               "woo_commerce_ept.view_woo_order_data_queue_ept_form"],
                   "import_completed_orders": ["woo_commerce_ept.action_woo_shipped_order_queue_ept",
                                               "woo_commerce_ept.view_woo_order_data_queue_ept_form"],
                   "import_coupon": ["woo_commerce_ept.action_woo_coupon_data_queue_ept",
                                     "woo_commerce_ept.view_woo_coupon_data_queue_ept_form"],
                   "import_specific_products": ["woo_commerce_ept.action_woo_product_data_queue_ept",
                                                "woo_commerce_ept.woo_product_data_queue_form_view_ept"],
                   "import_specific_orders": ["woo_commerce_ept.action_woo_unshipped_order_queue_ept",
                                              "woo_commerce_ept.view_woo_order_data_queue_ept_form"],
                   "export_stock": ["woo_commerce_ept.action_woo_export_stock_queue",
                                    "woo_commerce_ept.woo_export_stock_form_view_ept"]}

        if self.woo_operation == "import_customer":
            queues = self.sudo().woo_import_customers()
        elif self.woo_operation == "import_product":
            queues = self.sudo().get_products_from_woo()
        elif self.woo_operation == "import_product_tags":
            # self.sudo().sync_product_tags()
            self.env['woo.tags.ept'].woo_sync_product_tags(self.woo_instance_id)
        elif self.woo_operation == "import_attribute":
            # self.sudo().sync_woo_attributes()
            self.env['woo.product.template.ept'].sync_woo_attribute(self.woo_instance_id)
        elif self.woo_operation == "import_category":
            # self.sudo().sync_woo_product_category()
            self.env['woo.product.categ.ept'].sudo().sync_woo_product_category(self.woo_instance_id,
                                                                               sync_images_with_product=self.woo_instance_id.sync_images_with_product)
        elif self.woo_operation == "import_unshipped_orders":
            queues = self.sudo().import_sale_orders()
        elif self.woo_operation == "import_completed_orders":
            queues = self.sudo().import_sale_orders(order_type='completed')
        elif self.woo_operation == "import_cancel_orders":
            self.env["sale.order"].sudo().import_woo_cancel_order(self.woo_instance_id, self.orders_after_date,
                                                                  self.orders_before_date)
        elif self.woo_operation == "is_update_order_status":
            self.sudo().update_order_status()
        elif self.woo_operation == 'import_stock':
            self.sudo().import_stock()
        elif self.woo_operation == "export_stock":
            queues = self.sudo().update_stock_in_woo()
        elif self.woo_operation == "update_tags":
            self.sudo().update_tags_in_woo()
        elif self.woo_operation == "export_tags":
            self.sudo().export_tags_in_woo()
        elif self.woo_operation == "update_category":
            self.sudo().update_product_categ()
        elif self.woo_operation == "export_category":
            self.sudo().export_product_categ()
        elif self.woo_operation == "import_coupon":
            queues = self.sudo().import_woo_coupon()
        elif self.woo_operation == "export_coupon":
            self.sudo().export_woo_coupons()
        elif self.woo_operation == "update_coupon":
            self.sudo().update_woo_coupons()
        elif self.woo_operation == "import_product_from_csv":
            self.sudo().map_product_operation()
        elif self.woo_operation == "import_specific_products":
            queues = self.sudo().import_specific_product()
        elif self.woo_operation == "import_specific_orders":
            queues = self.sudo().import_specific_orders()

        if queues:
            action = self.env.ref(actions[self.woo_operation][0]).sudo().read()[0]
            if len(queues) > 1:
                action["domain"] = [("id", "in", queues)]
            else:
                form_view = [(self.env.ref(actions[self.woo_operation][1]).id, "form")]
                action['views'] = form_view
                action['res_id'] = queues[0]
            return action

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def set_video_based_on_operation(self):
        """
        This method is used to set video link based on operation
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 22 June 2022.
        Task_id: 193396 - Add video link while perform operation
        """
        if self.woo_operation in ['import_product', 'import_product_from_csv']:
            self.woo_video_url = 'https://www.youtube.com/watch?v=QYLiYrBKVQ4&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=2'

        if self.woo_operation == 'import_customer':
            self.woo_video_url = 'https://www.youtube.com/watch?v=2TtqPNmtKYM&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=16'

        if self.woo_operation == 'import_unshipped_orders':
            self.woo_video_url = 'https://www.youtube.com/watch?v=h53fY6A3QRI&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=6'

        if self.woo_operation == 'import_completed_orders':
            self.woo_video_url = 'https://www.youtube.com/watch?v=ZeJVWxDxaPE&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=8'

        if self.woo_operation == 'is_update_order_status':
            self.woo_video_url = 'https://www.youtube.com/watch?v=CAtfQtFurUM&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=7'

        if self.woo_operation == 'import_stock':
            self.woo_video_url = 'https://www.youtube.com/watch?v=inT-bUKRS9U&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=12'

        if self.woo_operation == 'export_stock':
            self.woo_video_url = 'https://www.youtube.com/watch?v=gNkT9NNW9RE&list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=11'

    def import_specific_product(self):
        """
        This method use for create product queue base specific product ids
        @author : Nilam Kubavat at 11-Aug-2022
        @task ID : 197960
        """
        start = time.time()
        import_all = self.import_products_method == "import_all"
        product_queues = []
        product_res_list = []
        # self.sync_woo_product_category(self.woo_instance_id)
        self.env['woo.product.categ.ept'].sync_woo_product_category(self.woo_instance_id,
                                                                    sync_images_with_product=self.woo_instance_id.sync_images_with_product)
        # self.sync_product_tags(self.woo_instance_id)
        self.env['woo.tags.ept'].woo_sync_product_tags(self.woo_instance_id)

        # self.sync_woo_attributes(self.woo_instance_id)
        self.env['woo.product.template.ept'].sync_woo_attribute(self.woo_instance_id)

        for template_id in list(self.woo_template_ids.split(",")):
            results, total_pages = self.env['woo.product.template.ept'].get_templates_from_woo(self.woo_instance_id,
                                                                                               from_date="", to_date="",
                                                                                               template_id=int(
                                                                                                   template_id))
            product_res_list.append(results[0])
        if product_res_list:
            product_queues = self.env['woo.product.template.ept'].with_context(
                import_export_record=self.id).create_woo_product_queue(product_res_list, self.woo_instance_id,
                                                                       import_all, template_id=False)
            end = time.time()
            _logger.info("Created product queues time -- %s -- seconds.", str(end - start))

        return product_queues

    def import_specific_orders(self):
        """
        This method use for get order queue base specific order ids
        @author : Nilam Kubavat at 11-Aug-2022
        @task ID : 197960
        """
        order_queues = self.env['sale.order'].import_woo_specific_orders(self.woo_instance_id,
                                                                         order_ids=self.woo_order_ids)
        return order_queues

    # def sync_woo_product_category(self, woo_instance=False):
    #     """
    #     This method is used for create a woo product category based on category response.
    #     :param woo_instance: It contains the browsable object of the current instance.
    #     :return: It will return True if the process successfully completed.
    #     @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
    #     Migrated by Maulik Barad on Date 07-Oct-2021.
    #     """
    #     woo_category_obj = self.env['woo.product.categ.ept']
    #
    #     if self:
    #         woo_instance = self.woo_instance_id
    #
    #     woo_category_obj.sync_woo_product_category(woo_instance,
    #                                                sync_images_with_product=woo_instance.sync_images_with_product)
    #
    #     self._cr.commit()
    #
    #     return True
    #
    # def sync_woo_attributes(self, woo_instance=False):
    #     """
    #     This method is used for create a product attribute with its values based on received product attributes
    #     response.
    #     :param woo_instance: It contains the browsable object of the current instance
    #     :return: It will return true if the process successful complete
    #     @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
    #     Migrated by Maulik Barad on Date 07-Oct-2021.
    #     """
    #     woo_template_obj = self.env['woo.product.template.ept']
    #
    #     if self:
    #         woo_instance = self.woo_instance_id
    #
    #     woo_template_obj.sync_woo_attribute(woo_instance)
    #
    #     return True
    #
    # def sync_product_tags(self, woo_instance=False):
    #     """
    #     This method is used for create a product tags based on received response of product tags.
    #     :param woo_instance: It contains the browsable object of the current instance
    #     :return: It will return True if the process successfully completed
    #     @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
    #     Migrated by Maulik Barad on Date 07-Oct-2021.
    #     """
    #     product_tags_obj = self.env['woo.tags.ept']
    #
    #     if self:
    #         woo_instance = self.woo_instance_id
    #
    #     product_tags_obj.woo_sync_product_tags(woo_instance)
    #
    #     return True

    def woo_import_customers(self):
        """
        This method used for get customers and generate queue for import process.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 August 2020.
        Task_id: 165956
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        start = time.time()
        res_partner_obj = self.env['res.partner']

        customer_queues = res_partner_obj.woo_get_customers(self.woo_instance_id)

        end = time.time()
        _logger.info("Created customer queues in %s seconds.", str(end - start))

        return customer_queues

    def prepare_data_and_import_stock(self):
        """
        This method is used for prepare data for import stock.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd 16-Nov-2019
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product = self.env['woo.product.product.ept']
        instance = self.woo_instance_id
        products_stock = {}
        duplicate_woo_product = []
        log_lines = []

        woo_products = woo_product.search([('exported_in_woo', '=', True), ('woo_instance_id', '=', instance.id)])
        sku = woo_products.mapped('default_code')
        product_fields = 'id,name,sku,manage_stock,stock_quantity'

        for sku_chunk in split_every(100, sku):
            res_products, log_lines = self.request_for_import_stock(sku_chunk, instance, product_fields, log_lines)
            for res_product in res_products:
                if isinstance(res_product, str):
                    continue
                products_stock, duplicate_woo_product, log_lines = self.prepare_data_for_inventory_adjustment(
                    woo_products, res_product, duplicate_woo_product, products_stock, log_lines)

        return products_stock

    def request_for_import_stock(self, sku_chunk, instance, product_fields, log_lines):
        """
        This method is used call request for the import stock.
        @param sku_chunk: A Bunch of woo template sku
        @param instance:
        @param product_fields: Domain for which value need in response.
        @param log_lines:
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 November 2020 .
        Task_id: 168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_response = []
        try:
            wcapi = instance.woo_connect()
            str_sku = ",".join(sku_chunk)
            res = wcapi.get("products", params={'sku': str_sku, '_fields': product_fields, 'per_page': 100})
            if res.status_code not in [200, 201]:
                log_line_id = self.env["common.log.lines.ept"].create_common_log_line_ept(
                    operation_type="import", module="woocommerce_ept", woo_instance_id=instance.id,
                    model_name="woo.product.product.ept", message="Import Stock for products has not proper "
                                                                  "response.\n Response %s" % res.content)
                log_lines.append(log_line_id.id)

            product_response = res.json()

        except Exception as error:
            log_line_id = self.env["common.log.lines.ept"].create_common_log_line_ept(
                operation_type="import", module="woocommerce_ept", woo_instance_id=instance.id,
                model_name="woo.product.product.ept", message="Import Stock for products not perform.\n Error %s" %
                                                              error)
            log_lines.append(log_line_id.id)

        return product_response, log_lines

    def prepare_data_for_inventory_adjustment(self, woo_products, res_product, duplicate_woo_product, products_stock,
                                              log_lines):
        """
        This method is used to prepare a data for inventory adjustment.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 November 2020 .
        Task_id: 168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product = woo_products.filtered(lambda x: x.default_code == res_product.get('sku'))
        if product:
            if res_product.get('manage_stock') and res_product.get('stock_quantity') and \
                    product.product_id.detailed_type == 'product':
                if product.product_id.id not in duplicate_woo_product:
                    _logger.info("Adding qty for inventory adjustment of Woo product: %s for "
                                 "Variant ID: %s", product.name, product.variant_id)
                    products_stock.update({product.product_id.id: res_product.get('stock_quantity')})
                    duplicate_woo_product.append(product.product_id.id)
                else:
                    _logger.info("Duplicate product found in WooCommerce store with SKU: %s ", product.default_code)
        else:
            log_line_id = self.env["common.log.lines.ept"].create_common_log_line_ept(
                operation_type="import", module="woocommerce_ept", woo_instance_id=woo_products[0].woo_instance_id.id,
                model_name="woo.product.product.ept",
                message="Import Stock for product %s does not exist in odoo" % res_product.get('sku'))
            log_lines.append(log_line_id.id)

        return products_stock, duplicate_woo_product, log_lines

    def import_stock(self):
        """
        This method is used for import stock. In which call methods for prepare stock data.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 08-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        instance = self.woo_instance_id
        inventory_name = "WooCommerce_%s_%s" % (instance.name, datetime.now().strftime("%d-%m-%Y"))

        products_stock = self.prepare_data_and_import_stock()

        if products_stock:
            _logger.info("Going for the create inventory adjustment....")
            self.env['stock.quant'].create_inventory_adjustment_ept(products_stock,
                                                                    instance.woo_warehouse_id.lot_stock_id,
                                                                    self.auto_apply_adjustments,
                                                                    inventory_name)
            _logger.info("Created inventory adjustment and inventory adjustment line.")
        return True

    def update_stock_in_woo(self):
        """
        This method call child method for update stock from Odoo to Woocommerce.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 16-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        instance = self.woo_instance_id
        queues = self.env['woo.product.template.ept'].update_stock(instance, self.export_stock_from)

        return queues

    def get_products_from_woo(self):
        """
        This method used to get products with its variants from WooCommerce store.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        start = time.time()
        woo_products_template_obj = self.env['woo.product.template.ept']

        woo_instance_id = self.woo_instance_id
        import_all = self.import_products_method == "import_all"

        # self.sync_woo_product_category(woo_instance_id)
        self.env['woo.product.categ.ept'].sync_woo_product_category(woo_instance_id,
                                                                    sync_images_with_product=woo_instance_id.sync_images_with_product)
        # self.sync_product_tags(woo_instance_id)
        self.env['woo.tags.ept'].woo_sync_product_tags(woo_instance_id)
        # self.sync_woo_attributes(woo_instance_id)
        self.env['woo.product.template.ept'].sync_woo_attribute(woo_instance_id)

        product_queues = woo_products_template_obj.with_context(
            import_export_record=self.id).get_products_from_woo_v1_v2_v3(woo_instance_id, import_all=import_all,
                                                                         from_date=self.products_after_date,
                                                                         to_date=self.products_before_date)
        to_date = fields.Datetime.now()
        woo_instance_id.import_products_last_date = to_date.astimezone(pytz.timezone("UTC")).replace(tzinfo=None)
        end = time.time()
        _logger.info("Created product queues in %s seconds.", str(end - start))

        return product_queues

    def woo_import_products(self, woo_products, created_by="import"):
        """
        This method used to create a new product queue based on received product response from woocommerce.
        @param : self :- It contain the object of current class
        @param : woo_products - It contain the products of woo commerce and its type is list
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_synced_queue_line_obj = self.env['woo.product.data.queue.line.ept']
        is_sync_image_with_product = 'done'
        queue_obj = self.create_product_queue(created_by)
        _logger.info("Product Data Queue %s created. Adding data in it.....", queue_obj.name)
        queue_obj_list = [queue_obj]
        sync_queue_vals_line = self.prepare_product_queue_line_vals(queue_obj)
        if self.woo_instance_id.sync_images_with_product:
            is_sync_image_with_product = 'pending'
        for woo_product in woo_products:
            existing_product_queue_line_data = woo_product_synced_queue_line_obj.search(
                [('woo_instance_id', '=', self.woo_instance_id.id), ('woo_synced_data_id', '=', woo_product.get('id')),
                 ('state', 'in', ['draft', 'failed'])])
            if not existing_product_queue_line_data:
                sync_queue_vals_line.update(
                    {
                        'woo_synced_data': json.dumps(woo_product),
                        'woo_update_product_date': woo_product.get('date_modified'),
                        'woo_synced_data_id': woo_product.get('id'),
                        'name': woo_product.get('name'),
                        'image_import_state': is_sync_image_with_product
                    })
                woo_product_synced_queue_line_obj.create(sync_queue_vals_line)
            else:
                existing_product_queue_line_data.write({'woo_synced_data': json.dumps(woo_product)})
            if len(queue_obj.queue_line_ids) == 101:
                queue_obj = self.create_product_queue(created_by)
                _logger.info("Product Data Queue %s created. Adding data in it.....", queue_obj.name)
                queue_obj_list.append(queue_obj)
                sync_queue_vals_line = self.prepare_product_queue_line_vals(queue_obj)

        for queue_obj in queue_obj_list:
            if not queue_obj.queue_line_ids:
                queue_obj.unlink()
        return queue_obj

    def create_product_queue(self, created_by):
        """
        This method used to create a product data queue.
        @return: product_queue: Record of product queue.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13 August 2020.
        Task_id:165892
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_synced_queue_obj = self.env['woo.product.data.queue.ept']
        queue_vals = {
            'name': self.woo_operation,
            'woo_instance_id': self.woo_instance_id.id,
            'woo_skip_existing_products': self.woo_skip_existing_product,
            "created_by": created_by
        }
        product_queue = woo_product_synced_queue_obj.create(queue_vals)
        return product_queue

    def prepare_product_queue_line_vals(self, product_queue):
        """
        This method used to prepare a vals for the product data queue line.
        :param product_queue: Record of product queue.
        @return: sync_queue_vals_line
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13 August 2020.
        Task_id:165892
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        sync_queue_vals_line = {
            'woo_instance_id': self.woo_instance_id.id,
            'synced_date': datetime.now(),
            'last_process_date': datetime.now(),
            'queue_id': product_queue.id
        }
        return sync_queue_vals_line

    def woo_export_products(self):
        """
        This method use to export selected product in the Woocommerce store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 15 September 2020 .
        Task_id: 165897
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_tmpl_obj = self.env['woo.product.template.ept']
        woo_instance_obj = self.env['woo.instance.ept']
        woo_template_ids = self._context.get('active_ids')

        if not woo_template_ids:
            raise UserError(_("Please select some products to Export to WooCommerce Store."))

        if woo_template_ids and len(woo_template_ids) > 80:
            raise UserError(_("Error:\n- System will not export more then 80 Products at a "
                              "time.\n- Please select only 80 product for export."))

        instances = woo_instance_obj.search([('active', '=', True)])

        woo_product_templates = woo_product_tmpl_obj.search([('id', 'in', woo_template_ids),
                                                             ('exported_in_woo', '=', False)])

        for instance in instances:
            woo_templates = woo_product_templates.filtered(lambda x: x.woo_instance_id == instance)
            if not woo_templates:
                continue
            woo_templates = self.woo_filter_templates(woo_templates)

            self.import_export_category_tag(instance)

            woo_product_tmpl_obj.export_products_in_woo(instance, woo_templates, self.woo_is_set_price,
                                                        self.woo_publish, self.woo_is_set_image, self.woo_basic_detail)
        return True

    def import_export_category_tag(self, instance):
        """
        This method is used to import-export the category and tag.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 November 2020 .
        Task_id:168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ_obj = self.env['woo.product.categ.ept']
        woo_tags_obj = self.env["woo.tags.ept"]

        domain = [('exported_in_woo', '=', False), ('woo_instance_id', '=', instance.id)]
        not_exported_category = woo_product_categ_obj.search(domain)
        if not_exported_category:
            # self.sync_woo_product_category(instance)
            self.env['woo.product.categ.ept'].sync_woo_product_category(instance,
                                                                        sync_images_with_product=instance.sync_images_with_product)
            not_exported_category = woo_product_categ_obj.search(domain)
            not_exported_category and woo_product_categ_obj.export_product_categs(instance, not_exported_category)

        not_exported_tag = woo_tags_obj.search(domain)
        if not_exported_tag:
            # self.sync_product_tags(instance)
            self.env['woo.tags.ept'].woo_sync_product_tags(instance)
            not_exported_tag = woo_tags_obj.search(domain)
            woo_tags_obj.woo_export_product_tags(instance, not_exported_tag)

    def woo_filter_templates(self, woo_templates):
        """
        This method is used for filter the woo product template based on default_code and woo template id
        :param woo_templates: It contain the woo product templates and Its type is Object
        :return: It will return the browsable object of the woo product template
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        filter_templates = []

        for woo_template in woo_templates:
            if not self.env['woo.product.product.ept'].search([('woo_template_id', '=', woo_template.id),
                                                               ('default_code', '=', False)]):
                filter_templates.append(woo_template)

        return filter_templates

    def import_sale_orders(self, order_type=""):
        """
        Imports woo orders and makes queues for selected instance.
        @author: Maulik Barad on Date 14-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_queues = self.env['sale.order'].import_woo_orders(self.woo_instance_id, self.orders_after_date,
                                                                self.orders_before_date, order_type=order_type)
        return order_queues

    def update_order_status(self):
        """
        This method used to call child method of update order status.
        @param : self
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 September 2020 .
        Task_id: 165894
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        self.env['sale.order'].update_woo_order_status(self.woo_instance_id)

    def update_products(self):
        """
        This method is used to update the existing products in woo commerce
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        start = time.time()
        woo_instance_obj = self.env['woo.instance.ept']
        woo_product_tmpl_obj = self.env['woo.product.template.ept']

        if not self.woo_basic_detail and not self.woo_is_set_price and not self.woo_is_set_image and not \
                self.woo_publish:
            raise UserError(_('Please Select any one Option for process Update Products'))

        woo_tmpl_ids = self._context.get('active_ids')
        if woo_tmpl_ids and len(woo_tmpl_ids) > 80:
            raise UserError(_("Error\n- System will not update more then 80 Products at a "
                              "time.\n- Please select only 80 product for update."))

        instances = woo_instance_obj.search([('active', '=', True)])
        woo_tmpl_ids = woo_product_tmpl_obj.browse(woo_tmpl_ids)
        for instance in instances:
            woo_templates = woo_tmpl_ids.filtered(lambda x: x.woo_instance_id.id == instance.id and x.exported_in_woo)
            if not woo_templates:
                continue
            if self.woo_basic_detail:
                self.import_export_category_tag(instance)

            woo_product_tmpl_obj.update_products_in_woo(instance, woo_templates, self.woo_is_set_price,
                                                        self.woo_publish, self.woo_is_set_image, self.woo_basic_detail)
        end = time.time()
        _logger.info("Update products in Woocommerce Store in %s seconds.", str(end - start))
        return True

    def export_stock_in_woo(self):
        """
        This method use to export stock for selected Woo template.
        @param : self
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 15 September 2020 .
        Task_id: 166453
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_instance_obj = self.env['woo.instance.ept']
        woo_product_tmpl_obj = self.env['woo.product.template.ept']
        export_stock_data_obj = self.env['woo.export.stock.queue.ept']
        woo_tmpl_ids = self._context.get('active_ids')

        if woo_tmpl_ids and len(woo_tmpl_ids) > 80:
            raise UserError(_("Error\n- System will not update more then 80 Products at a time.\n- Please select only "
                              "80 product for update."))

        instances = woo_instance_obj.search([('active', '=', True)])
        for instance in instances:
            woo_templates = woo_product_tmpl_obj.search(
                [('woo_instance_id', '=', instance.id), ('id', 'in', woo_tmpl_ids),
                 ('exported_in_woo', '=', True)])
            if not woo_templates:
                continue
            odoo_products = woo_templates.woo_product_ids.mapped('product_id').ids
            export_stock_queue_id = woo_product_tmpl_obj.with_context(
                updated_products_in_inventory=odoo_products).woo_create_queue_for_export_stock(instance,
                                                                                               woo_templates)
            if export_stock_queue_id:
                queue_ids = export_stock_queue_id
                export_stock_data_queue = export_stock_data_obj.browse(queue_ids)
                if not export_stock_data_queue.export_stock_queue_line_ids:
                    export_stock_data_queue.unlink()
                    return True
                action_name = "woo_commerce_ept.action_woo_export_stock_queue"
                form_view_name = "woo_commerce_ept.woo_export_stock_form_view_ept"
                if queue_ids and action_name and form_view_name:
                    action = self.env.ref(action_name).sudo().read()[0]
                    form_view = self.sudo().env.ref(form_view_name)

                    if len(queue_ids) == 1:
                        action.update({"view_id": (form_view.id, form_view.name), "res_id": queue_ids[0],
                                       "views": [(form_view.id, "form")]})
                    else:
                        action["domain"] = [("id", "in", queue_ids)]
                    return action
        return True

    def update_export_category_tags_coupons_in_woo(self):
        """
        This common method will be called from wizard of Update/Export Category and Tags.
        @author: Maulik Barad on Date 14-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        process_type = self._context.get("process", "")
        if process_type == "update_category":
            self.update_product_categ()
        elif process_type == "export_category":
            self.export_product_categ()
        elif process_type == "update_tags":
            self.update_tags_in_woo()
        elif process_type == "export_tags":
            self.export_tags_in_woo()
        elif process_type == "export_coupon":
            self.export_woo_coupons()
        elif process_type == "update_coupon":
            self.update_woo_coupons()
        return {'type': 'ir.actions.client',
                'tag': 'reload'}

    def export_tags_in_woo(self):
        """
        Exports tags in WooCommerce, which are not exported.
        @author: Maulik Barad on Date 13-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_tags_obj = self.env["woo.tags.ept"]

        if self._context.get("process", "") == "export_tags":
            tags_need_to_export = woo_tags_obj.search(
                [("id", "in", self._context.get("active_ids")), ("exported_in_woo", "=", False)])
        else:
            tags_need_to_export = woo_tags_obj.search(
                [("woo_instance_id", "=", self.woo_instance_id.id), ("exported_in_woo", "=", False)])
        woo_tags_obj.woo_export_product_tags(tags_need_to_export.woo_instance_id, tags_need_to_export)

    def update_tags_in_woo(self):
        """
        Updates tags in WooCommerce, which are not exported.
        @author: Maulik Barad on Date 13-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_tags_obj = self.env["woo.tags.ept"]
        if self._context.get("process", "") == "update_tags":
            tags_need_to_export = woo_tags_obj.search(
                [("id", "in", self._context.get("active_ids")), ("exported_in_woo", "=", True)])
        else:
            tags_need_to_export = woo_tags_obj.search(
                [("woo_instance_id", "=", self.woo_instance_id.id), ("exported_in_woo", "=", True)])
        woo_tags_obj.woo_update_product_tags(tags_need_to_export.woo_instance_id, tags_need_to_export)

    def update_product_categ(self):
        """
        This method used to search Woocommerce category for update.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13/12/2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_categ_obj = self.env['woo.product.categ.ept']
        instance_obj = self.env['woo.instance.ept']
        woo_categ_ids = self._context.get('active_ids')

        if woo_categ_ids and self._context.get('process'):
            instances = instance_obj.search([("active", "=", True)])
            for instance in instances:
                woo_product_categs = product_categ_obj.search(
                    [('woo_categ_id', '!=', False), ('woo_instance_id', '=', instance.id),
                     ('exported_in_woo', '=', True), ('id', 'in', woo_categ_ids)])
                woo_product_categs and product_categ_obj.update_product_categs_in_woo(instance,
                                                                                      woo_product_categs)
        else:
            woo_product_categs = product_categ_obj.search(
                [('woo_categ_id', '!=', False),
                 ('woo_instance_id', '=', self.woo_instance_id.id),
                 ('exported_in_woo', '=', True)])
            woo_product_categs and product_categ_obj.update_product_categs_in_woo(
                self.woo_instance_id, woo_product_categs)
        return True

    def export_product_categ(self):
        """
        This method used to search Woocommerce category for export.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14/12/2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_categ_obj = self.env['woo.product.categ.ept']
        instance_obj = self.env['woo.instance.ept']
        woo_categ_ids = self._context.get('active_ids')

        # This is called while export product categories from Action
        if woo_categ_ids and self._context.get('process'):
            instances = instance_obj.search([("active", "=", True)])
            for instance in instances:
                woo_product_categs = product_categ_obj.search(
                    [('woo_instance_id', '=', instance.id), ('exported_in_woo', '=', False),
                     ('id', 'in', woo_categ_ids)])
                if woo_product_categs:
                    product_categ_obj.export_product_categs(instance, woo_product_categs)
        # This is called while export product categories from WooCommerce Operations
        else:
            woo_product_categs = product_categ_obj.search(
                [('woo_instance_id', '=', self.woo_instance_id.id), ('exported_in_woo', '=', False)])
            if woo_product_categs:
                product_categ_obj.export_product_categs(self.woo_instance_id, woo_product_categs)
        return True

    def import_woo_coupon(self):
        """
        This method is used to import coupons from Woocommerce to Odoo.
        @author: Nilesh Parmar on date 17 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        """Below method is used to sync the product category from Woocommerce to Odoo"""
        # self.sync_woo_product_category()
        self.env['woo.product.categ.ept'].sync_woo_product_category(self.woo_instance_id,
                                                                    sync_images_with_product=self.woo_instance_id.sync_images_with_product)
        coupon_queue = self.env['woo.coupons.ept'].sync_woo_coupons(self.woo_instance_id)

        return coupon_queue

    def export_woo_coupons(self):
        """
        This method is used to export coupons from Odoo to Woocommerce store.
        @author: Nilesh Parmar on date 17 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        coupons_obj = self.env['woo.coupons.ept']
        coupons_ids = self._context.get('active_ids')

        if coupons_ids and self._context.get('process'):
            instances = self.env['woo.instance.ept'].search([("active", "=", True)])
            for instance in instances:
                woo_coupons = coupons_obj.search(
                    [('woo_instance_id', '=', instance.id), ('exported_in_woo', '=', False),
                     ('id', 'in', coupons_ids)])
                if not woo_coupons:
                    continue
                woo_coupons.export_coupons(instance)
        else:
            woo_coupons = coupons_obj.search(
                [('woo_instance_id', '=', self.woo_instance_id.id), ('exported_in_woo', '=', False)])
            if woo_coupons:
                woo_coupons.export_coupons(self.woo_instance_id)

    def update_woo_coupons(self):
        """
        This method is used to update coupons from Odoo to Woocommerce store.
        @author: Nilesh Parmar on date 17 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        coupon_obj = self.env['woo.coupons.ept']
        coupon_ids = self._context.get('active_ids')
        if coupon_ids and self._context.get('process'):
            coupon_ids = coupon_obj.search(
                [('id', 'in', coupon_ids), ('coupon_id', '!=', False), ('exported_in_woo', '=', True)])
        else:
            coupon_ids = coupon_obj.search(
                [('coupon_id', '!=', False), ('woo_instance_id', '=', self.woo_instance_id.id),
                 ('exported_in_woo', '=', True)])

        if coupon_ids:
            coupon_ids.update_woo_coupons(coupon_ids.woo_instance_id)

    def map_product_operation(self):
        """
        Perform map product operation.
        """
        try:
            if os.path.splitext(self.file_name)[1].lower() not in ['.csv', '.xls', '.xlsx']:
                raise UserError(_("Invalid file format. You are only allowed to upload .csv, .xlsx file."))
            if os.path.splitext(self.file_name)[1].lower() == '.csv':
                self.import_products_from_csv()
            else:
                self.import_products_from_xlsx()
        except Exception as error:
            raise UserError(_("Receive the error while import file. %s", error))

    def import_products_from_csv(self):
        """
        This method used to import products using CSV file which imported in Woo product layer.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        file_data = self.read_csv_file()
        self.file_required_header_validation(file_data.fieldnames)
        self.create_products_from_file(file_data)
        return True

    def import_products_from_xlsx(self):
        """
        This method used to import product using xlsx file in shopify layer.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 3 December 2021 .
        Task_id: 180490 - Prepare for export changes
        """
        header, product_data = self.read_xlsx_file()
        self.file_required_header_validation(header)
        self.create_products_from_file(product_data)
        return True

    def file_required_header_validation(self, header):
        """
        This method is used to check the required field is existing in a csv or xlsx file or not.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 November 2020 .
        Task_id: 168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        required_fields = ['template_name', 'product_name', 'product_default_code',
                           'woo_product_default_code', 'product_description', 'sale_description',
                           'PRODUCT_TEMPLATE_ID', 'PRODUCT_ID', 'CATEGORY_ID']
        for required_field in required_fields:
            if required_field not in header:
                raise UserError(_("Required Column %s Is Not Available In CSV File") % required_field)

    def create_products_from_file(self, file_data):
        """
        This method is used to create products in Woo product layer from the file.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 3 December 2021 .
        Task_id: 180490 - Prepare for export changes
        """
        instance_id = self.woo_instance_id

        if not self.choose_file:
            raise UserError(_('Please Select the file for start process of Product Sync'))

        row_no = 0
        product_tmpl_list = []
        for record in file_data:
            if not record['PRODUCT_TEMPLATE_ID'] or not record['PRODUCT_ID']:
                self.create_csv_mismatch_log_line(record, row_no, instance_id)
                row_no += 1
                continue

            product_tmpl_id = record['PRODUCT_TEMPLATE_ID']
            if product_tmpl_id not in product_tmpl_list:
                woo_template = self.create_or_update_woo_template(instance_id, record)

            product_tmpl_list.append(product_tmpl_id)

            self.create_or_update_woo_variant(instance_id, record, woo_template)

            row_no += 1

        return True

    def create_csv_mismatch_log_line(self, record, row_no, instance):
        """
        This method used to create a mismatch log line while csv or xlsx processing for import product.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 November 2020 .
        Task_id:168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        message = ""
        if not record['PRODUCT_TEMPLATE_ID']:
            if message:
                message += ', \n'
            message += 'Product Template Id not available in Row Number %s' % row_no
        if not record['PRODUCT_ID']:
            if message:
                message += ', \n'
            message += 'Product Id not available in Row Number %s' % row_no
        common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                       woo_instance_id=instance.id, model_name=self._name,
                                                       message=message)

    def read_csv_file(self):
        """
        Read selected .csv file based on delimiter
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        :return: It will return the object of csv file data
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        self.write({'csv_data': self.choose_file})
        self._cr.commit()
        import_file = BytesIO(base64.decodebytes(self.csv_data))
        file_read = StringIO(import_file.read().decode())
        reader = csv.DictReader(file_read, delimiter=',')
        return reader

    def read_xlsx_file(self):
        """
        Read selected .xlsx file based on delimiter
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd
        :return: It will return the list of xlsx file data
        """
        validation_header = []
        product_data = []
        sheets = xlrd.open_workbook(file_contents=base64.b64decode(self.choose_file.decode('UTF-8')))
        header = dict()
        is_header = False
        for sheet in sheets.sheets():
            for row_no in range(sheet.nrows):
                if not is_header:
                    headers = [d.value for d in sheet.row(row_no)]
                    validation_header = headers
                    [header.update({d: headers.index(d)}) for d in headers]
                    is_header = True
                    continue
                row = dict()
                [row.update({k: sheet.row(row_no)[v].value}) for k, v in header.items() for c in
                 sheet.row(row_no)]
                product_data.append(row)
        return validation_header, product_data

    def create_or_update_woo_template(self, instance_id, record):
        """
        This method uses to create/update the Woocmmerce layer template.
        @return: woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_tmpl_obj = self.env['product.template']
        woo_product_template = self.env['woo.product.template.ept']
        category_obj = self.env['product.category']
        woo_prepare_product_for_export_obj = self.env['woo.prepare.product.for.export.ept']
        woo_category_dict = {}
        woo_template = woo_product_template.search([('woo_instance_id', '=', instance_id.id),
                                                    ('product_tmpl_id', '=', int(record['PRODUCT_TEMPLATE_ID']))])
        product_template = product_tmpl_obj.browse(int(record['PRODUCT_TEMPLATE_ID']))
        if len(product_template.product_variant_ids) == 1:
            product_type = 'simple'
        else:
            product_type = 'variable'

        woo_template_vals = self.preapre_template_vals_from_csv_data(record, instance_id, product_type)

        categ_id = category_obj.browse(int(record.get('CATEGORY_ID'))) if record.get('CATEGORY_ID') else ''

        if categ_id:
            woo_prepare_product_for_export_obj.create_categ_in_woo(categ_id, instance_id.id,
                                                                   woo_category_dict)
            woo_categ_id = woo_prepare_product_for_export_obj.update_category_info(categ_id, instance_id.id)
            woo_template_vals.update({'woo_categ_ids': [(6, 0, woo_categ_id.ids)]})

        if not woo_template:
            woo_template = woo_product_template.create(woo_template_vals)
        else:
            woo_template.write(woo_template_vals)

        # Translate vals based on instance language.
        woo_prepare_product_for_export_obj.set_value_base_on_language(product_template, instance_id, woo_template_vals,
                                                                      woo_template)
        # For adding all odoo images into Woo layer.
        woo_prepare_product_for_export_obj.create_woo_template_images(woo_template)

        return woo_template

    def preapre_template_vals_from_csv_data(self, record, instance_id, product_type):
        """
        This method is used to prepare a woo template data from CSV file.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 November 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_vals = {
            'product_tmpl_id': int(record['PRODUCT_TEMPLATE_ID']),
            'woo_instance_id': instance_id.id,
            'name': record['template_name'],
            'woo_product_type': product_type
        }

        if self.env["ir.config_parameter"].sudo().get_param("woo_commerce_ept.set_sales_description"):
            woo_template_vals.update({'woo_description': record.get('sale_description'),
                                      'woo_short_description': record.get('product_description')})
        return woo_template_vals

    def create_or_update_woo_variant(self, instance_id, record, woo_template):
        """
        This method uses to create/update the Woocmmerce layer variant.
        @return: woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_obj = self.env['woo.product.product.ept']
        woo_prepare_product_for_export_obj = self.env['woo.prepare.product.for.export.ept']
        woo_variant = woo_product_obj.search(
            [('woo_instance_id', '=', instance_id.id), ('product_id', '=', int(record['PRODUCT_ID'])),
             ('woo_template_id', '=', woo_template.id)])

        woo_variant_vals = ({
            'woo_instance_id': instance_id.id,
            'product_id': int(record['PRODUCT_ID']),
            'woo_template_id': woo_template.id,
            'default_code': record['woo_product_default_code'],
            'name': record['product_name'],
        })

        if not woo_variant:
            woo_variant = woo_product_obj.create(woo_variant_vals)
        else:
            woo_variant.write(woo_variant_vals)

        # For adding all odoo images into Woo layer.
        woo_prepare_product_for_export_obj.create_woo_variant_images(woo_template, woo_variant)

        return woo_variant

    def woo_check_running_schedulers(self, cron_xml_id):
        """
        This method is used to check that seleted operation cron is running or not.
        :param cron_xml_id: Xml id of the scheduler action.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 5 November 2020 .
        Task_id: 167715
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        try:
            cron_id = self.env.ref('woo_commerce_ept.%s%d' % (cron_xml_id, self.woo_instance_id.id))
        except Exception as error:
            return
        if cron_id and cron_id.sudo().active:
            res = cron_id.try_cron_lock()
            if not res:
                res = {}
            if res and res.get('reason') or res.get('result') == 0:
                message = "You are not allowed to run this process.The Scheduler is already started the Process."
                self.cron_process_notification = message
                self.is_hide_execute_button = True
            if res and res.get('result'):
                self.cron_process_notification = "This process is also performed by a scheduler, and the next " \
                                                 "schedule for this process will run in %s minutes." % res.get('result')
            elif res and res.get('reason'):
                self.cron_process_notification = res.get('reason')

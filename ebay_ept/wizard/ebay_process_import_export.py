#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes product import export process.
"""
import base64
import csv
import io
import os
from io import StringIO, BytesIO
from csv import DictWriter
from datetime import datetime, timedelta
import logging
import xlrd
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import xlsxwriter

_logger = logging.getLogger(__name__)


class EbayProcessImportExport(models.TransientModel):
    """
    Describes eBay Process for import/ export products
    """
    _name = "ebay.process.import.export"
    _description = "eBay Process Import Export"
    is_get_feedback = fields.Boolean(string='Get FeedBack', help="This Field relocate check feedback True/False.")
    seller_id = fields.Many2one(
        'ebay.seller.ept', string='eBay Seller', help="This Field relocate seller of eBay.")
    instance_ids = fields.Many2many(
        "ebay.instance.ept", 'ebay_instance_import_export_rel', 'process_id', 'instance_id',
        string="Select Sites", help="This Field relocate site.")
    operations = fields.Selection([
        ('get_ebay_details', 'GeteBayDetails & UserPreferences'),
        ('ebay_sync_import_products', 'Import Products'),
        ('map_ebay_products', 'Map eBay Products'),
        ('ebay_import_categories', 'Import Categories'),
        ('ebay_import_store_categories', 'Import Store Categories'),
        ('get_ebay_feedBack', 'Get FeedBack'),
        ('ebay_import_unshipped_order', 'Import Unshipped orders'),
        ('ebay_import_shipped_order', 'Import Shipped Orders'),
        ('update_stock_from_odoo_to_eBay', 'Export Stock'),
        ('update_price_from_odoo_to_eBay', 'Update Price'),
        ('update_order_status_from_odoo_to_eBay', 'Update Order Status From Odoo to eBay')
    ], string='eBay Operations', help="This Field relocate eBay Operation.")
    is_export_images = fields.Boolean(
        string="Export Images", default=False, help="This field relocate export images.")
    level_limit = fields.Integer(
        string="Category Level Limit", default=1, help="This Field relocate define category limit.")
    only_leaf_categories = fields.Boolean(
        string="Only Leaf eBay Categories", default=True, help="This Field relocate check eBay leaf categories.")
    store_level_limit = fields.Integer(
        string="Store Category Level Limit", default=1, help="This Field relocate store category level limit.")
    store_only_leaf_categories = fields.Boolean(
        string="Only Store Leaf eBay Categories", default=True,
        help="This Field relocate check only store leaf eBay categories.")
    from_date = fields.Date(string="From", help="This Field relocate from date.")
    to_date = fields.Date(string="To", help="This Field relocate end date.")
    max_name_levels = fields.Integer(
        string='Max Names Level', default=10,
        help="This field can be used if you want to limit the number of Item Specifics names"
             " that are returned for each eBay category. "
             "If you only wanted to retrieve the three most popular Item"
             " Specifics names per category, "
             "you would include this field and set its value to 3.")
    max_value_per_name = fields.Integer(
        string='Max Values Per Name', default=25,
        help="This field can be used if you want to limit the number of Item Specifics values "
             "(for each Item Specifics name) that are returned for each eBay category. "
             "If you only wanted to retrieve the 10 most popular Item Specifics values "
             "per Item Specifics name per category, "
             "you would include this field and set its value to 10.")
    is_import_get_item_condition = fields.Boolean(
        string='Get-Item Condition', default=False, help="Category wise import item condition.")
    is_create_auto_odoo_product = fields.Boolean(
        string="Auto Create Odoo Product ?", default=False,
        help="If this option is checked, then it will allow to create new Odoo product when it is not found.")
    is_sync_stock = fields.Boolean(
        string="Sync Stock ?", default=False,
        help="When you select this option, It will sync product stock of Odoo & eBay.")
    is_sync_price = fields.Boolean(
        string="Sync Price ?", default=False,
        help="When you select this option, It will sync product price of Odoo & eBay.")
    is_import_shipped_order = fields.Boolean(
        string="Import Shipped Order", default=False, help="Import shipped order from the eBay.")
    shipped_order_from_date = fields.Datetime(string="Order From Date", help="Select import shipped order From Date.")
    shipped_order_to_date = fields.Datetime(string="Order To Date", help="Select import shipped order To Date")
    ebay_import_csv_data = fields.Binary(string="Choose File")
    ebay_import_csv_filename = fields.Char(string='Filename')
    ebay_export_product_method = fields.Selection(
        [("direct", "Export in eBay Layer"), ("csv", "Export in CSV file"), ("xlsx", "Export in XLSX file")],
        default="direct", string="Export Method")
    export_stock_from = fields.Datetime(help="It is used for exporting stock from Odoo to eBay.")

    @api.constrains('level_limit', 'store_level_limit')
    def _check_level_limit(self):
        for record in self:
            if record.level_limit not in range(0, 11):
                raise UserError(_("The Category Level Limit should be between 0 and 10."))
            if record.store_level_limit not in range(0, 11):
                raise UserError(_("The Store Category Level Limit should be between 0 and 10."))

    def execute(self):
        """
        Execute different eBay operations based on selected operation,
        """
        if self.operations == 'ebay_sync_import_products':
            return getattr(self, str(self.operations))(self.seller_id)
        instance_ids = self.get_selected_ebay_instances()
        return getattr(self, str(self.operations))(instance_ids)

    def get_selected_ebay_instances(self):
        """
        Search and return instances if instance is not selected.
        :return: ebay instance object.
        """
        instance_ids = self.instance_ids
        if not self.instance_ids or self.operations == "map_ebay_products":
            instance_ids = self.seller_id.instance_ids
        return instance_ids

    @staticmethod
    def action_redirect_to_specific_page(action_name, model_name, view_mode, domain, view_id=False, res_id=False):
        """
        Action to redirect on specific page.
        :param action_name: Name of Action
        :param model_name: Res Model name
        :param view_mode: Action view mode
        :param domain: Domain if any
        :param view_id: If true, it will be added view Id for the action.
        :param res_id: If true, it will be added res Id for the action.
        :return: redirect to the specific page.
        """
        result = {
            'name': _(action_name), 'view_mode': view_mode, 'res_model': model_name,
            'type': 'ir.actions.act_window', 'domain': domain, 'target': 'current'}
        if view_id:
            result.update({'views': [(view_id, 'form')], 'view_id': view_id, 'res_id': res_id})
        return result

    def get_ebay_details(self, instance_ids, seller_id=False):
        """
        Perform operation for getting eBay details.
        :param seller_id: seller id
        :param instance_ids:  eBay instance object
        """
        seller_id = seller_id if seller_id else self.seller_id
        results = self.get_ebay_result(seller_id)
        if results:
            self.env['ebay.payment.options'].get_payment_options(
                seller_id, results.get('PaymentOptionDetails', []))
            self.env['ebay.site.details'].get_site_details(results.get('SiteDetails', False))
            for instance in instance_ids:
                self.update_ebay_result(instance, results)
            self.ebay_get_user_preferences(instance_ids)

    def ebay_get_user_preferences(self, instance_ids):
        """
        Perform operation for getting eBay user preference.
        :param instance_ids: eBay Instance object
        :return: Redirect to the eBay Site policy page.
        """
        result = True
        ebay_site_policy_obj = self.env['ebay.site.policy.ept']
        ebay_policies_ids = []
        for instance in instance_ids:
            ebay_policies = ebay_site_policy_obj.sync_policies(instance)
            for ebay_policies_id in ebay_policies:
                ebay_policies_ids.append(ebay_policies_id)

        if isinstance(ebay_policies_ids, list) and ebay_policies_ids:
            result = self.action_redirect_to_specific_page(
                'eBay Site Policies', 'ebay.site.policy.ept', 'tree,form',
                "[('id', 'in', " + str(ebay_policies_ids) + " )]")
        return result

    def ebay_sync_import_products(self, seller_id):
        """
        This method is used to import product from eBay store to Odoo, it will import the product base on given date
        range and create product data queue.
        @param seller_id: Records of ebay seller
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 December 2021 .
        Task_id: 180923 - Map Products
        """
        product_data_queue_obj = self.env["ebay.import.product.queue"]
        if self._context.get('is_call_from_cron'):
            is_create_odoo_products = seller_id.create_new_product
            is_sync_product_stock = seller_id.ebay_is_sync_stock
            is_sync_product_price = seller_id.ebay_is_sync_price
        else:
            is_create_odoo_products = self.is_create_auto_odoo_product
            is_sync_product_stock = self.is_sync_stock
            is_sync_product_price = self.is_sync_price
        date_range = self.prepare_date_range_for_import_product(seller_id)
        product_queue_list = []
        for seller in seller_id:
            existing_product_queue = False
            for from_date, to_date in date_range:
                product_result = self.sync_import_products(seller, from_date, to_date)
                if not bool(product_result[0]):
                    continue
                product_queue, last_product_queue = product_data_queue_obj.create_product_queue(seller,
                                                                                                product_result,
                                                                                                existing_product_queue,
                                                                                                is_create_odoo_product=is_create_odoo_products,
                                                                                                is_sync_stock=is_sync_product_stock,
                                                                                                is_sync_price=is_sync_product_price)
                product_queue_list += product_queue
                if product_queue:
                    product_queue_cron = self.env.ref("ebay_ept.ir_cron_child_to_process_product_queue")
                    if not product_queue_cron.active:
                        _logger.info("Active the product queue cron job")
                        product_queue_cron.write({'active': True, 'nextcall': datetime.now() + timedelta(seconds=120)})
                if len(last_product_queue.import_product_queue_line_ids) > 50:
                    existing_product_queue = last_product_queue
        if product_queue_list:
            action_name = "ebay_ept.action_ebay_import_product_queue_ept"
            form_view_name = "ebay_ept.view_ebay_import_product_queue_form"
            return self.redirect_to_view(action_name, form_view_name, product_queue_list)
        return True

    def prepare_date_range_for_import_product(self, seller_id):
        """
        This method is use to prepare date range for import products. eBay allow 119 days date ranges,
        so as per import wizard date, prepare list of 119 days difference.
        @return: List of date range.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 December 2021 .
        Task_id: 180923 - Map Products
        """
        if self._context.get('is_call_from_cron'):
            from_date = seller_id.sync_active_products_start_date
            to_date = datetime.now().date()
            seller_id.sync_active_products_start_date = to_date
        else:
            from_date = self.from_date
            to_date = self.to_date
        date_range = []
        while True:
            to_date_tmp = from_date + timedelta(days=119)
            if to_date_tmp > to_date:
                date_range.append((datetime.strftime(from_date, DEFAULT_SERVER_DATE_FORMAT),
                                   datetime.strftime(to_date, DEFAULT_SERVER_DATE_FORMAT)))
                break
            date_range.append((datetime.strftime(from_date, DEFAULT_SERVER_DATE_FORMAT),
                               datetime.strftime(to_date_tmp, DEFAULT_SERVER_DATE_FORMAT)))
            from_date = to_date_tmp
        return date_range

    def sync_import_products(self, seller, from_date, to_date):

        """
        This method is use to import the products from eBay to Odoo.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        from_date = "%sT00:00:00.000Z" % from_date
        to_date = "%sT00:00:00.000Z" % to_date
        page_number = 1
        result_final = []
        while True:
            products = {}
            try:
                trade_api = seller.get_trading_api_object()
                para = {
                    'DetailLevel': 'ItemReturnDescription', 'StartTimeFrom': from_date, 'StartTimeTo': to_date,
                    'IncludeVariations': True, 'Pagination': {'EntriesPerPage': 100, 'PageNumber': page_number},
                    'IncludeWatchCount': True}
                trade_api.execute('GetSellerList', para)
                results = trade_api.response.dict()
                if results and results.get('Ack', False) == 'Success' and results.get('ItemArray', {}):
                    products = results['ItemArray'].get('Item', [])
            except Exception as error:
                raise UserError(_('%s', str(error)))
            has_more_trans = results.get('HasMoreItems', 'false')
            if isinstance(products, dict):
                products = [products]
            for result in products:
                result_final = result_final + [result]
            if has_more_trans == 'false':
                break
            page_number = page_number + 1
        return result_final

    def map_ebay_products(self, instance_ids):
        """
        This method is use to import product from csv,xlsx.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id:180923 - Map Products
        """
        try:
            if os.path.splitext(self.ebay_import_csv_filename)[1].lower() not in ['.csv', '.xls', '.xlsx']:
                raise UserError(_("Invalid file format. You are only allowed to upload .csv, .xlsx file."))
            if os.path.splitext(self.ebay_import_csv_filename)[1].lower() == '.csv':
                ebay_templates = self.import_products_from_csv()
            else:
                ebay_templates = self.import_products_from_xlsx()

            if ebay_templates:
                action_name = "ebay_ept.action_ebay_product_template_ept"
                form_view_name = "ebay_ept.ebay_product_template_form_view_ept"
                return self.redirect_to_view(action_name, form_view_name, ebay_templates)
        except Exception as error:
            raise UserError(_("Receive the error while process file. %s", error))

    def import_products_from_csv(self):
        """
        This method is use to import/map product from CSV file.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id:180923 - Map Products
        """
        list_product = self.read_csv_file()
        self.validate_required_csv_header(list_product[0].keys())
        ebay_templates = self.create_products_from_file(list_product)
        return ebay_templates

    def read_csv_file(self):
        """
        Read selected .csv file based on delimiter
        :return: It will return the object of csv file data
        """
        import_file = BytesIO(base64.decodebytes(self.ebay_import_csv_data))
        file_read = StringIO(import_file.read().decode())
        reader = csv.DictReader(file_read, delimiter=',')
        return [row for row in reader]

    def validate_required_csv_header(self, header):
        """
        This method is used to validate required csv header while csv file import for products.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id: 180923 - Map Products
        """
        required_fields = ["template_name", "product_name", "product_default_code",
                           "ebay_sku", "product_template_id", "product_id"]

        for required_field in required_fields:
            if required_field not in header:
                raise UserError(_("Required column is not available in File."))

    def create_products_from_file(self, product_data):
        """
        This method is use to create products in ebay product layer from file.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 8 December 2021 .
        Task_id: 180923 - Map Products
        """
        ebay_templates = []
        log_line_obj = self.env['common.log.lines.ept']
        row_no = 1
        for instance in self.instance_ids:
            for product_dic in product_data:
                row_no += 1
                if not product_dic["product_template_id"] or not product_dic["product_id"]:
                    message = "product_template_id Or product_id As Per Odoo Product in file at row " \
                              "%s " % row_no
                    log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                            model_name='ebay.process.import.export',
                                                            log_line_type='fail', mismatch=True,
                                                            ebay_instance_id=instance.id)
                    continue
                ebay_template = self.create_update_ebay_product(instance, product_dic)
                if ebay_template.id not in ebay_templates:
                    ebay_templates.append(ebay_template.id)
        return ebay_templates

    def create_update_ebay_product(self, instance, product_dic):
        """
        This method is use to create update product in eBay product layer.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id: 180923 - Map Products
        """
        product_template_obj = self.env['product.template']
        odoo_template = product_template_obj.browse(int(product_dic['product_template_id']))
        ebay_template = self.create_update_ebay_product_template(odoo_template, instance.id)
        self.create_or_update_ebay_product_variant_in_layer(instance, ebay_template, product_dic)
        return ebay_template

    def import_products_from_xlsx(self):
        """
        This method is use to import product data from the xlsx file.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021.
        Task_id: 180923 - Map Products
        """
        validation_header, product_data = self.read_xlsx_file()
        self.validate_required_csv_header(validation_header)
        ebay_templates = self.create_products_from_file(product_data)
        return ebay_templates

    def read_xlsx_file(self):
        """
        This method is use to read the xlsx file data.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id: 180923 - Map Products
        """
        validation_header = []
        product_data = []
        sheets = xlrd.open_workbook(file_contents=base64.b64decode(self.ebay_import_csv_data.decode('UTF-8')))
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
                [row.update({k: sheet.row(row_no)[v].value}) for k, v in header.items() for c in sheet.row(row_no)]
                product_data.append(row)
        return validation_header, product_data

    def ebay_import_categories(self, instance_ids):
        """
        This method is use to import the categories from eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 22 December 2021 .
        Task_id: 180142 - Import Categories
        """
        category_obj = self.env['ebay.category.master.ept']
        ebay_category_list = category_obj.import_category(instance_ids, self.level_limit, self.only_leaf_categories,
                                                          self.is_import_get_item_condition)
        if isinstance(ebay_category_list, list) and ebay_category_list:
            action_name = "ebay_ept.action_category_master"
            form_view_name = "ebay_ept.view_category_master_form"
            return self.redirect_to_view(action_name, form_view_name, ebay_category_list)
        return True

    def ebay_import_store_categories(self, instance_ids):
        """
        Perform operation to import store categories.
        :param instance_ids: eBay instance object
        :return: action to redirect to the product categories page
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .
        """
        category_obj = self.env['ebay.category.master.ept']
        ebay_store_category = category_obj.import_store_category(instance_ids, self.store_level_limit,
                                                                 self.store_only_leaf_categories)
        if isinstance(ebay_store_category, list) and ebay_store_category:
            action_name = "ebay_ept.action_store_category_master"
            form_view_name = "ebay_ept.view_category_master_form"
            return self.redirect_to_view(action_name, form_view_name, ebay_store_category)
        return True

    def get_ebay_feedBack(self, instance_ids):
        """
        Perform operation to get Feedbacks from eBay.
        :param instance_ids: eBay instance object
        :return: action to redirect to the eBay feedback page.
        """
        ebay_feedback_obj = self.env['ebay.feedback.ept']
        result = True
        ebay_feedback_ids = ebay_feedback_obj.get_feedback(instance_ids)
        if isinstance(ebay_feedback_ids, list) and ebay_feedback_ids:
            result = self.action_redirect_to_specific_page('eBay FeedBack', 'ebay.feedback.ept', 'tree,form',
                                                           "[('id', 'in', " + str(ebay_feedback_ids) + " )]")
        return result

    def ebay_import_unshipped_order(self, instance_ids):
        """
        Perform operation to import unshipped orders from eBay.
        Migration done by Haresh Mori @ Emipro on date 5 January 2022 .
        """
        ebay_order_data_queue_obj = self.env['ebay.order.data.queue.ept']
        order_queues = ebay_order_data_queue_obj.import_unshipped_orders_from_ebay(self.seller_id)
        if order_queues:
            action_name = "ebay_ept.action_ebay_order_data_queue_ept"
            form_view_name = "ebay_ept.view_ebay_order_data_queue_ept_form"
            return self.redirect_to_view(action_name, form_view_name, order_queues)

    def ebay_import_shipped_order(self, instance_ids):
        """
        Perform operation to import shipped orders from eBay and create queue.
        :return: action to redirect to the order data queue page.
        """
        ebay_order_data_queue_obj = self.env['ebay.order.data.queue.ept']
        order_queues = ebay_order_data_queue_obj.import_shipped_orders_from_ebay(self.seller_id,
                                                                                 self.shipped_order_to_date,
                                                                                 self.shipped_order_from_date)
        if order_queues:
            action_name = "ebay_ept.action_ebay_order_data_queue_ept"
            form_view_name = "ebay_ept.view_ebay_order_data_queue_ept_form"
            return self.redirect_to_view(action_name, form_view_name, order_queues)
        return True

    def update_stock_from_odoo_to_eBay(self, instance_ids):
        """
        This method is use to udpate stock from product stock from Odoo to eBay.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 January 2022 .
        Task_id: 180143 - Update product Stock and Price
        """
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        for instance in instance_ids:
            ebay_product_product_obj.export_stock_in_ebay(instance)

    def update_price_from_odoo_to_eBay(self, instance_ids):
        """
        Perform operation to update price from Odoo to eBay.
        :param instance_ids: eBay instance object.
        """
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        for instance in instance_ids:
            ebay_product_product_obj.update_price_in_ebay(instance)

    def update_order_status_from_odoo_to_eBay(self, instance_ids):
        """
        Perform operation to update order status into eBay.
        :param instance_ids: eBay instance object
        """
        sale_order_obj = self.env['sale.order']
        for instance in instance_ids:
            sale_order_obj.ebay_update_order_status(instance)

    @staticmethod
    def get_ebay_result(seller):
        """
        Get eBay instance details from eBay API.
        :param seller: current instance of eBay
        :returns: GeteBayDetails API response
        """
        trading_api = seller.get_trading_api_object()
        para = {}
        # pass parameters in GeteBayDetails sandbox API is temporary.
        # Because in sandbox shipping services are not fetched.
        # once API works perfect, pass parameter code will be removed.
        if seller.environment == 'is_sandbox':
            para = {
                "DetailName": [
                    "SiteDetails", "PaymentOptionDetails", "ReturnPolicyDetails",
                    "BuyerRequirementDetails", "ShippingLocationDetails"]}
        trading_api.execute('GeteBayDetails', para)
        results = trading_api.response.dict()
        return results

    @api.model
    def update_ebay_result(self, instance, results):
        """
        Update eBay site details, payment options, refunds, shipping details.
        :param instance: instance of eBay
        :param results: response received from Getebaydetails API
        """
        ebay_shipping_service_obj = self.env['ebay.shipping.service']
        shipping_locations_obj = self.env['ebay.shipping.locations']
        exclude_shipping_locations_obj = self.env['ebay.exclude.shipping.locations']
        refund_options_obj = self.env['ebay.refund.options']
        feedback_score_obj = self.env['ebay.feedback.score']
        refund_options_obj.create_refund_details(instance, results.get('ReturnPolicyDetails', {}))
        feedback_score_obj.create_buyer_requirement(instance, results.get('BuyerRequirementDetails', {}))
        results_first_array = results.get('ShippingServiceDetails', [])
        results_second_array = results.get('ExcludeShippingLocationDetails', [])
        results_third_array = results.get('ShippingLocationDetails', [])
        ebay_shipping_service_obj.shipping_service_create(results_first_array, instance)
        exclude_shipping_locations_obj.create_exclude_shipping_locations(
            results_second_array, instance
        )
        shipping_locations_obj.create_shipping_locations(results_third_array, instance)
        buyer_requirement = results.get('BuyerRequirementDetails', {})
        ship_to_register_country = buyer_requirement.get('ShipToRegistrationCountry', False)
        instance.write({
            'is_primary_shipping_address': ship_to_register_country == 'true'
        })
        return True

    def get_ebay_item_conditions(self):
        """
        Get category item conditions from eBay API
        """
        category_obj = self.env['ebay.category.master.ept']
        active_ids = self._context.get('active_ids')
        categs = category_obj.browse(active_ids)
        for categ in categs:
            categ.get_item_conditions()
        return True

    def get_ebay_attributes(self):
        """
        This method is use to get the category attribute from eBay.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 23 December 2021 .
        Task_id: 180142 - Import Categories
        """
        category_obj = self.env['ebay.category.master.ept']
        active_ids = self._context.get('active_ids')
        categories = category_obj.browse(active_ids)
        max_name_levels = self.max_name_levels
        max_value_per_name = self.max_value_per_name
        if max_name_levels and max_name_levels > 30 or max_name_levels < 1:
            raise UserError(_("Max Names Level has max value is 30 and min value is 1"))
        if max_value_per_name and max_value_per_name > 2147483647 or max_value_per_name < 1:
            raise UserError(_("Max Value Per Name has max value is 2147483647 and min value is 1"))
        for category in categories:
            category.get_attributes(max_name_levels, max_value_per_name)
        return True

    def prepare_product_for_export_in_ebay(self):
        """
        This method is used to export products in eBay layer as per selection.
        If "direct" is selected, then it will direct export product into eBay layer.
        If "csv" is selected, then it will export product data in CSV file, if user want to do some
        modification in name, description, etc. before importing into eBay Layer.
        If "xlsx" is selected, then it will export product data in XLSX file, if user want to do some
        modification in name, description, etc. before importing into eBay Layer.
        """
        active_template_ids = self._context.get("active_ids", [])
        templates = self.env["product.template"].browse(active_template_ids)
        product_templates = templates.filtered(lambda template: template.type != "service")
        if not product_templates:
            raise UserError(_("It seems like selected products are not Storable products."))

        if self.ebay_export_product_method == "direct":
            return self.prepare_product_for_export(product_templates)
        elif self.ebay_export_product_method == "csv":
            return self.export_product_in_csv(product_templates)
        elif self.ebay_export_product_method == "xlsx":
            return self.export_product_in_xlsx(product_templates)

    def export_product_in_csv(self, odoo_templates):
        """
        Create and download CSV file for export product in eBay Layer.
        :param odoo_templates: Odoo product template object
        """
        delimiter = ','
        products_list = self.prepare_product_data_for_import_file(odoo_templates)
        buffer = StringIO()
        field_names = list(products_list[0].keys())
        csv_writer = DictWriter(buffer, field_names, delimiter=delimiter)
        csv_writer.writer.writerow(field_names)
        csv_writer.writerows(products_list)
        buffer.seek(0)
        file_data = buffer.read().encode()
        self.write({'ebay_import_csv_data': base64.encodebytes(file_data)})
        filename = 'ebay_product_export' + str(datetime.now().strftime("%d/%m/%Y:%H:%M:%S"))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=ebay.process.import.export&csv_wizard_id=%s'
                   '&filename=%s.csv' % (self.id, filename),
            'target': 'self',
        }

    def export_product_in_xlsx(self, odoo_templates):
        """
        This method is used to prepare data for the xlsx file.
        @param odoo_templates: Records of Odoo template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 December 2021 .
        Task_id: 180923 - Map Products
        """
        products_list = self.prepare_product_data_for_import_file(odoo_templates)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Map Product')
        header = list(products_list[0].keys())
        header_format = workbook.add_format({'bold': True, 'font_size': 10})
        general_format = workbook.add_format({'font_size': 10})
        worksheet.write_row(0, 0, header, header_format)
        index = 0
        for product in products_list:
            index += 1
            worksheet.write_row(index, 0, list(product.values()), general_format)
        workbook.close()
        b_data = base64.b64encode(output.getvalue())
        self.write({
            "ebay_import_csv_data": b_data,
        })
        filename = 'ebay_product_export' + str(datetime.now().strftime("%d/%m/%Y:%H:%M:%S"))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=ebay.process.import.export&csv_wizard_id=%s'
                   '&filename=%s.xlsx' % (self.id, filename),
            'target': 'self',
        }

    def prepare_product_data_for_import_file(self, odoo_templates):
        """
        This method is used to prepare product data vals for export file in CSV/XLSX file
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 December 2021 .
        Task_id: 180923 - Map Products
        """
        products_list = []
        for odoo_template in odoo_templates:
            for variant in odoo_template.product_variant_ids:
                product_dict = self.prepare_product_variant_data_dict(odoo_template, variant)
                products_list.append(product_dict)
        return products_list

    def prepare_product_variant_data_dict(self, odoo_template, variant):
        """
        This method is use to prepare product variant data dictionary.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 December 2021 .
        Task_id: 180923 - Map Products
        """
        product_dict = {
            'template_name': odoo_template.name,
            'product_name': variant.name,
            'product_default_code': variant.default_code,
            'ebay_sku': variant.default_code,
            'product_template_id': odoo_template.id,
            'product_id': variant.id,
        }
        return product_dict

    def prepare_product_for_export(self, odoo_templates):
        """
        Add product and product template into eBay Layer.
        :param odoo_templates: Odoo product template object
        :return:
        """
        ebay_template_list = []
        instance_ids = self.get_selected_ebay_instances()
        for instance in instance_ids:
            for odoo_template in odoo_templates:
                ebay_template = self.create_update_ebay_product_template(odoo_template, instance.id)
                for variant in odoo_template.product_variant_ids:
                    if not variant.default_code:
                        continue
                    product_dic = {'product_id': variant.id, 'ebay_sku': variant.default_code,
                                   'product_name': variant.name}
                    self.create_or_update_ebay_product_variant_in_layer(instance, ebay_template, product_dic)
                ebay_template_list.append(ebay_template.id)
        if ebay_template_list:
            action_name = "ebay_ept.action_ebay_product_template_ept"
            form_view_name = "ebay_ept.ebay_product_template_form_view_ept"
            return self.redirect_to_view(action_name, form_view_name, ebay_template_list)
        return True

    def create_update_ebay_product_template(self, odoo_template, instance_id):
        """
        Create eBay product template when map with odoo products
        :param odoo_template: product template object
        :param instance_id: eBay instance id
        :return: ebay product template object
        """
        ebay_template_obj = self.env['ebay.product.template.ept']
        ebay_template = ebay_template_obj.search(
            [('instance_id', '=', instance_id), ('product_tmpl_id', '=', odoo_template.id)], limit=1)
        if not ebay_template:
            ebay_template_object = self.env['ebay.product.template.ept']
            odoo_attr_ids = []
            attribute_line_ids = odoo_template.attribute_line_ids
            for attribute_line_id in attribute_line_ids:
                odoo_attr_ids.append(attribute_line_id.attribute_id.id)

            ebay_template = ebay_template_object.create({
                'instance_id': instance_id,
                'product_tmpl_id': odoo_template.id,
                'name': odoo_template.name,
                'description': odoo_template.description_sale,
                'product_attribute_ids': [(6, 0, odoo_attr_ids)]
            })
        else:
            ebay_template.write({'name': odoo_template.name,
                                 'description': odoo_template.description_sale})
        return ebay_template

    def create_or_update_ebay_product_variant_in_layer(self, instance_id, ebay_template, product_dic):
        """
        This method is use to create ebay product variant in layer.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 December 2021 .
        Task_id: 180923 - Map Products
        """
        ebay_product_object = self.env['ebay.product.product.ept']
        variant_id = int(product_dic['product_id'])
        ebay_prod_sku = product_dic['ebay_sku']
        variant_name = product_dic['product_name']
        ebay_variant = ebay_product_object.search([
            ('instance_id', '=', instance_id.id), ('product_id', '=', variant_id), ('ebay_product_tmpl_id', '=',
                                                                                    ebay_template.id)])
        if not ebay_variant:
            ebay_product_object.create({
                'instance_id': instance_id.id,
                'product_id': variant_id,
                'ebay_product_tmpl_id': ebay_template.id,
                'ebay_sku': ebay_prod_sku,
                'name': variant_name
            })
        else:
            ebay_variant.write({'ebay_sku': ebay_prod_sku, 'name': variant_name})

    def redirect_to_view(self, action_name, form_view_name, list_of_ids):
        """
        This method is use to redirect tree/from view
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 8 December 2021 .
        Task_id:180923 - Map Products
        """
        action = self.env.ref(action_name).sudo().read()[0]
        form_view = self.sudo().env.ref(form_view_name)

        if len(list_of_ids) == 1:
            action.update({"view_id": (form_view.id, form_view.name), "res_id": list_of_ids[0],
                           "views": [(form_view.id, "form")]})
        else:
            action["domain"] = [("id", "in", list_of_ids)]
        return action

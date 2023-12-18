# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
import requests
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..img_upload import img_file_upload

_logger = logging.getLogger("WooCommerce")


class WooProductTemplateEpt(models.Model):
    _name = "woo.product.template.ept"
    _order = 'product_tmpl_id'
    _description = "WooCommerce Product Template"

    @api.depends('woo_product_ids.exported_in_woo', 'woo_product_ids.variant_id')
    def _compute_total_sync_variants(self):
        """
        :param : self :- It is the browsable object of woo product template class
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        """
        woo_product_obj = self.env['woo.product.product.ept']
        for template in self:
            variants = woo_product_obj.search(
                [('id', 'in', template.woo_product_ids.ids), ('exported_in_woo', '=', True),
                 ('variant_id', '!=', False)])
            template.total_sync_variants = len(variants)

    name = fields.Char(translate=True)
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1)
    product_tmpl_id = fields.Many2one("product.template", "Product Template", required=1, ondelete="cascade")
    active = fields.Boolean(default=True)
    woo_description = fields.Html("Description", translate=True)
    woo_short_description = fields.Html("Short Description", translate=True)
    taxable = fields.Boolean(default=True)
    woo_tmpl_id = fields.Char("Woo Template Id", size=120)
    exported_in_woo = fields.Boolean()
    website_published = fields.Boolean('Available in the website', copy=False)
    created_at = fields.Datetime()
    updated_at = fields.Datetime()
    total_variants_in_woo = fields.Integer(default=0, help="Total Variants in WooCommerce,Display after sync products")
    total_sync_variants = fields.Integer(compute="_compute_total_sync_variants", store=True)
    woo_product_ids = fields.One2many("woo.product.product.ept", "woo_template_id", "Products")

    woo_categ_ids = fields.Many2many('woo.product.categ.ept', 'woo_template_categ_rel', 'woo_template_id',
                                     'woo_categ_id', "Categories")
    woo_tag_ids = fields.Many2many('woo.tags.ept', 'woo_template_tags_rel', 'woo_template_id', 'woo_tag_id', "Tags")
    woo_product_type = fields.Selection([('simple', 'Simple'), ('variable', 'Variable'), ('bundle', 'Bundle'),
                                         ('grouped', 'Grouped'), ('external', 'External')])
    woo_image_ids = fields.One2many("woo.product.image.ept", "woo_template_id")
    is_virtual_product = fields.Boolean('Is Virtual Product?', copy=False,
                                        help="It is used to identify that product is virtual.")

    @api.onchange("product_tmpl_id")
    def on_change_product(self):
        """
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        for record in self:
            record.name = record.product_tmpl_id.name

    def write(self, vals):
        """
        This method use to archive/unarchive woo product variants base on woo product templates.
        :parameter: self, vals
        :return: res
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 09/12/2019.
        :Task id: 158502
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_product_obj = self.env['woo.product.product.ept']
        if 'active' in vals.keys():
            for woo_template in self:
                woo_template.woo_product_ids and woo_template.woo_product_ids.write({'active': vals.get('active')})
                if vals.get('active'):
                    woo_variants = woo_product_product_obj.search([
                        ('woo_template_id', '=', woo_template.id),
                        ('woo_instance_id', '=', woo_template.woo_instance_id.id),
                        ('active', '=', False)])
                    woo_variants and woo_variants.write({'active': vals.get('active')})
        res = super(WooProductTemplateEpt, self).write(vals)
        return res

    @api.model
    def get_variant_image(self, instance, variant):
        """
        This method is used for get the image of product and upload that image in woo commerce
        :param instance: It contains the browsable object of the current instance
        :param variant: It contains the woo product variant
        :return: return the image response in dictionary
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        image_id = False
        variation_data = {}
        variant_images = variant.woo_image_ids

        if variant_images:
            if not variant_images[0].woo_image_id:
                res = img_file_upload.upload_image(instance, variant_images[0].image,
                                                   "%s_%s" % (variant.name, variant.id),
                                                   variant_images[0].image_mime_type)
                image_id = res.get('id') if res else ''
            else:
                image_id = variant_images[0].woo_image_id

        if image_id:
            variation_data.update({"image": {'id': image_id}})
            variant_images[0].woo_image_id = image_id

        return variation_data

    @api.model
    def get_variant_data(self, variant, instance, update_image):
        """
        This method is used for prepare the product variant data with its image and return it into
        dictionary format
        :param variant: It contains the woo product variant
        :param instance: It contains the browsable object of the current instance
        :param update_image: It contains Either True or False
        :return: It will return the product variant details and its type is Dict.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        attrs = []
        woo_attribute_obj = self.env['woo.product.attribute.ept']
        variation_data = {}
        attr_data = {}
        for attribute_value in variant.product_id.product_template_attribute_value_ids:
            attribute_value_name = attribute_value.with_context(lang=instance.woo_lang_id.code).name
            attribute_name = attribute_value.attribute_id.with_context(lang=instance.woo_lang_id.code).name
            if instance.woo_attribute_type == 'select':
                woo_attribute = woo_attribute_obj.search([('name', '=', attribute_value.attribute_id.name),
                                                          ('woo_instance_id', '=', instance.id),
                                                          ('exported_in_woo', '=', True)], limit=1)
                if not woo_attribute:
                    woo_attribute = woo_attribute_obj.search([('attribute_id', '=', attribute_value.attribute_id.id),
                                                              ('woo_instance_id', '=', instance.id),
                                                              ('exported_in_woo', '=', True)], limit=1)
                attr_data = {
                    'id': woo_attribute and woo_attribute.woo_attribute_id,
                    'option': attribute_value_name
                }
            if instance.woo_attribute_type == 'text':
                attr_data = {
                    'name': attribute_name,
                    'option': attribute_value_name
                }
            attrs.append(attr_data)
        if update_image:
            variation_data.update(self.get_variant_image(instance, variant))

        weight = self.convert_weight_by_uom(variant.product_id.weight, instance)

        variation_data.update({'attributes': attrs, 'sku': str(variant.default_code),
                               'weight': str(weight), "manage_stock": variant.woo_is_manage_stock})
        return variation_data

    @api.model
    def get_product_price(self, instance, variant):
        """
        It will get the product price based on pricelist and return it
        :param instance: It contains the browsable object of the current instance
        :param variant: It contains the woo product variant
        :return: It will return the product regular price and sale price into Dict Format.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        vals = {}
        price, regular_price_rule = instance.woo_pricelist_id.get_product_price_list_rule(variant.product_id,
                                                                                          1.0,
                                                                                          partner=False)
        vals.update({'regular_price': str(price)})
        if instance.woo_extra_pricelist_id:
            sale_price, sale_price_rule = instance.woo_extra_pricelist_id.get_product_price_list_rule(
                variant.product_id,
                1.0,
                partner=False)
            if sale_price_rule:
                vals.update({'sale_price': str(sale_price) if sale_price > 0 else ""})
        return vals

    def prepare_batches(self, data):
        """
        This method is used for create batches
        :param data:  It can be either object or list
        :return: list of batches
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd
        :Task id: 156886
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        batches = []
        start, end = 0, 100
        if len(data) > 100:
            while True:
                data_batch = data[start:end]
                if not data_batch:
                    break
                temp = end + 100
                start, end = end, temp
                batches.append(data_batch)
        else:
            batches.append(data)
        return batches

    @api.model
    def woo_update_stock(self, instance, woo_templates):
        """
        This method is used for export stock from odoo to Woocommerce.
        :param instance: Instance Object
        :param woo_templates: Object of Woo Product Template
        :return: Boolean
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd On Data 19-Nov-2019
        :Task id: 156886
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        sale_order_obj = self.env['sale.order']
        log_lines = []
        wc_api = instance.woo_connect()
        woo_template_ids = self.check_available_products_in_woocommerce(wc_api, instance)
        if woo_template_ids:
            woo_templates = woo_templates.filtered(lambda template: template.id in woo_template_ids.ids)

        product_ids = woo_templates.woo_product_ids.product_id
        product_stock = self.check_stock_type(instance, product_ids)
        # For Simple products.
        simple_products = woo_templates.filtered(lambda x: x.woo_product_type == 'simple')
        if simple_products:
            log_lines += self.export_stock_simple_products(simple_products, product_stock, instance)

        # For Variable products.
        variable_products = woo_templates.filtered(lambda x: x.woo_product_type == 'variable')
        if variable_products:
            log_lines += self.export_stock_variable_products(variable_products, product_stock, instance)

        instance.write({'last_inventory_update_time': datetime.now()})
        if log_lines and instance.is_create_schedule_activity:
            sale_order_obj.woo_create_schedule_activity_against_logline(log_lines, instance)
        return True

    @api.model
    def woo_create_queue_for_export_stock(self, instance, woo_templates):
        """
        This method use for create export stock queue
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        export_stock_obj = self.env['woo.export.stock.queue.ept']
        queue_data = []
        queue_ids = False
        wc_api = instance.woo_connect()
        if not self._context.get('active_ids'):
            woo_template_ids = self.check_available_products_in_woocommerce(wc_api, instance)
            if woo_template_ids:
                woo_templates = woo_templates.filtered(lambda x: x.id in woo_template_ids.ids)

        product_ids = woo_templates.woo_product_ids.product_id
        product_stock = self.check_stock_type(instance, product_ids)
        # For Simple products.
        simple_products = woo_templates.filtered(lambda x: x.woo_product_type == 'simple')
        if simple_products:
            batches = self.prepare_batches(simple_products)
            for batch in batches:
                queue_data.append(
                    {'batch_details': self.prepare_simple_batch_export_stock_data(batch, product_stock),
                     'product_type': 'simple'})

        # For Variable products.
        for template in woo_templates.filtered(lambda x: x.woo_product_type == 'variable'):
            variations = self.prepare_variable_batch_export_stock_data(template, product_stock)
            if variations:
                variant_batches = self.prepare_batches(variations)
                queue_data.append(
                    {'batch_details': variant_batches,
                     'woo_tmpl_id': template.woo_tmpl_id,
                     'product_type': 'variable'})

        if queue_data:
            queues = export_stock_obj.create_woo_export_stock_queue(instance, queue_data)
            queue_ids = queues.ids

        instance.write({'last_inventory_update_time': datetime.now()})
        return queue_ids

    def check_stock_type(self, instance, product_ids):
        """
        This Method relocates check type of stock.
        :param instance: These arguments relocates instance of Woocommerce.
        :param product_ids: This arguments product listing id of odoo.
        :return: This Method return product listing stock.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        prod_obj = self.env['product.product']
        warehouse = instance.woo_stock_export_warehouse_ids
        products_stock = False
        if product_ids:
            if instance.woo_stock_field.name == 'free_qty':
                products_stock = prod_obj.get_free_qty_ept(warehouse, product_ids.ids)
            elif instance.woo_stock_field.name == 'virtual_available':
                products_stock = prod_obj.get_forecasted_qty_ept(warehouse, product_ids.ids)
            elif instance.woo_stock_field.name == 'qty_available':
                products_stock = prod_obj.get_onhand_qty_ept(warehouse, product_ids.ids)
        return products_stock

    def prepare_variable_batch_export_stock_data(self, woo_template, product_stock):
        """
        This method prepares stock data for batch update stock of variable products to WooCommerce.
        @param woo_template: Template record of Woo layer.
        @param product_stock: Stock data of products.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        variations = []
        for variant in woo_template.woo_product_ids.filtered(lambda x:
                                                             x.product_id.detailed_type == 'product' and
                                                             x.variant_id and x.woo_is_manage_stock):
            if variant.product_id.id in self._context.get('updated_products_in_inventory'):
                quantity = product_stock.get(variant.product_id.id)
                if variant.fix_stock_type == 'fix' and variant.fix_stock_value < quantity:
                    quantity = variant.fix_stock_value
                if variant.fix_stock_type == 'percentage':
                    percentage_stock = int((quantity * variant.fix_stock_value) / 100.0)
                    if percentage_stock < quantity:
                        quantity = percentage_stock

                variations.append({
                    'id': variant.variant_id,
                    'manage_stock': True,
                    'stock_quantity': int(quantity)
                })
        return variations

    def export_stock_variable_products(self, woo_variable_products, product_stock, instance):
        """
        This method used to export stock for variable products.
        @param : self,woo_variable_products,product_stock,instance
        @return: log_lines
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11 September 2020 .
        Task_id: 165895
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        log_lines = []
        common_log_line_obj = self.env["common.log.lines.ept"]

        wc_api = instance.woo_connect()
        _logger.info('Starting Process of Simple Product Export Stock.')
        for template in woo_variable_products:
            variations = self.prepare_variable_batch_export_stock_data(template, product_stock)
            if variations:
                variant_batches = self.prepare_batches(variations)
                for woo_variants in variant_batches:
                    _logger.info('Starting Variations Batch Stock Update Process of %s.', template.name)
                    try:
                        res = wc_api.post('products/%s/variations/batch' % template.woo_tmpl_id,
                                          {'update': woo_variants})
                    except Exception as error:
                        raise UserError(_("Something went wrong while Exporting Stock.\n\nPlease Check your Connection "
                                          "and Instance Configuration.\n\n" + str(error)))

                    _logger.info('Completed Variations Batch Stock Update Process Completed with [status: %s]',
                                 res.status_code)
                    log_line = self.check_woocommerce_response(res, "Update Product stock", "woo.product.product.ept",
                                                               instance)
                    if log_line and not isinstance(log_line, (dict, list)):
                        log_lines.append(log_line.id)

        _logger.info('Process of Variable Product Export Stock is completed.')
        return log_lines

    def check_woocommerce_response(self, response, process, model_name, instance, product_template=False,
                                   stock_queue_line=False):
        """
        This method verifies the response got from WooCommerce after Update/Export operations.
        @param product_template:
        @param instance:
        @param model_name:
        @param process: Name of the process.
        @param response: Response from Woo.
        @return: Log line if issue found.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        if process in ["WooCommerce Attributes", "Import Product"]:
            operation = "import"
        else:
            operation = "export"

        if not isinstance(response, requests.models.Response):
            message = process + "Response is not in proper format :: %s" % response
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=model_name,
                                                                  res_id=product_template and product_template.id,
                                                                  message=message,
                                                                  woo_export_stock_queue_line_id=stock_queue_line)
        if response.status_code not in [200, 201]:
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=model_name,
                                                                  res_id=product_template and product_template.id,
                                                                  message=response.content,
                                                                  woo_export_stock_queue_line_id=stock_queue_line)
        try:
            data = response.json()
        except Exception as error:
            message = "Json Error : While" + process + "\n%s" % error
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=model_name,
                                                                  res_id=product_template and product_template.id,
                                                                  message=message,
                                                                  woo_export_stock_queue_line_id=stock_queue_line)
        return data

    def prepare_simple_batch_export_stock_data(self, woo_products, product_stock):
        """
        This method prepares stock data for batch update stock of simple products to WooCommerce.
        @param woo_products: Products of Woo Layer.
        @param product_stock: Stock data of products.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        batch_update_data = []
        for template in woo_products:
            info = {'id': template.woo_tmpl_id, 'variations': []}
            variant = template.woo_product_ids[0]
            if variant.woo_is_manage_stock:
                quantity = product_stock.get(variant.product_id.id, 0)
                if variant.fix_stock_type == 'fix' and variant.fix_stock_value < quantity:
                    quantity = variant.fix_stock_value
                if variant.fix_stock_type == 'percentage':
                    percentage_stock = int((quantity * variant.fix_stock_value) / 100.0)
                    if percentage_stock < quantity:
                        quantity = percentage_stock
                info.update({'manage_stock': True, 'stock_quantity': int(quantity)})
                batch_update_data.append(info)
        return batch_update_data

    def export_stock_simple_products(self, woo_simple_products, product_stock, instance):
        """
        This method used to export stock for simple products.
        @param : self,woo_simple_products,product_stock,instance
        @return: log_lines
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11 September 2020.
        Task_id: 165895
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]

        wc_api = instance.woo_connect()
        _logger.info('Starting Process of Simple Product Export Stock.')
        batches = self.prepare_batches(woo_simple_products)
        log_lines = []
        for woo_products in batches:
            batch_update_data = self.prepare_simple_batch_export_stock_data(woo_products, product_stock)

            if batch_update_data:
                _logger.info('Starting Batch Products Stock Update Process.')
                try:
                    res = wc_api.post('products/batch', {'update': batch_update_data})
                except Exception as error:
                    raise UserError(_("Something went wrong while Exporting Stock.\n\nPlease Check your Connection and "
                                      "Instance Configuration.\n\n" + str(error)))
                _logger.info('Completed Product Batch Stock Update Process Completed with [Status: %s]',
                             res.status_code)
                log_line = self.check_woocommerce_response(res, "Update Product Stock", "woo.product.product.ept",
                                                           instance)
                response = {}
                if isinstance(log_line, (dict, list)):
                    response = log_line
                elif log_line:
                    log_lines.append(log_line.id)

                if response.get('data') and response.get('data', {}).get('status') != 200:
                    log_line = common_log_line_obj.create_common_log_line_ept(operation_type="export",
                                                                              module="woocommerce_ept",
                                                                              woo_instance_id=instance.id,
                                                                              model_name="woo.product.product.ept",
                                                                              message=response.get('message'))
                    log_lines.append(log_line.id)
        _logger.info('Process of Simple Product Export Stock is completed.')
        return log_lines

    def woo_unpublished(self):
        """
        This method is used for unpublish product from woo commerce store
        :return: It will return True If product successfully unpublished from woo
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        instance = self.woo_instance_id
        common_log_line_obj = self.env["common.log.lines.ept"]
        wc_api = instance.woo_connect()
        if self.woo_tmpl_id:
            try:
                res = wc_api.put('products/%s' % self.woo_tmpl_id, {'status': 'draft'})
            except Exception as error:
                raise UserError(_("Something went wrong while updating Product.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            response = self.check_woocommerce_response(res, "Unpublish Product", "woo.product.template.ept", instance)
            if not isinstance(response, (dict, list)):
                return False
            if response.get('data') and response.get('data', {}).get('status') not in [200, 201]:
                message = response.get('message')
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, message=message,
                                                               model_name="woo.product.template.ept")
            else:
                self.write({'website_published': False})
        return True

    def woo_published(self):
        """
        This method is used for publish product in woo commerce store
        @return: It will return True If product successfully published in woo
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        instance = self.woo_instance_id
        common_log_line_obj = self.env["common.log.lines.ept"]
        wc_api = instance.woo_connect()
        if self.woo_tmpl_id:
            try:
                res = wc_api.put('products/%s' % self.woo_tmpl_id, {'status': 'publish'})
            except Exception as error:
                raise UserError(_("Something went wrong while updating Product.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            response = self.check_woocommerce_response(res, "Publish Product", "woo.product.template.ept", instance)
            if not isinstance(response, (dict, list)):
                return False
            if response.get('data', {}) and response.get('data', {}).get('status') not in [200, 201]:
                message = response.get('message')
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, message=message,
                                                               model_name="woo.product.template.ept")
            else:
                self.write({'website_published': True})
        return True

    def import_all_attribute_terms(self, wc_api, woo_attribute_id, response, instance):
        """
        This method is used for get the attribute value response as per request by page wise and return it
        @param wc_api: It contains the connection object between odoo and woo
        @param woo_attribute_id: It contains the Woo product Attribute and its type is Object
        @return: It will return response based on send request
        @param response:
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """

        attribute_term_data = []
        total_pages = response.headers.get('x-wp-totalpages', 0) if response else 1
        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                params = {'per_page': 100, 'page': page}
                try:
                    res = wc_api.get("products/attributes/%s/terms" % woo_attribute_id.woo_attribute_id, params=params)
                except Exception as error:
                    raise UserError(_("Something went wrong while importing Attribute Values.\n\nPlease Check your "
                                      "Connection and Instance Configuration.\n\n" + str(error)))

                data = self.check_woocommerce_response(res, "WooCommerce Attribute Terms/Values",
                                                       "woo.product.attribute.term.ept", instance)
                if not isinstance(data, (dict, list)):
                    return []
                attribute_term_data += data

        return attribute_term_data

    def find_or_create_woo_attribute_term(self, attributes_term_data, instance, woo_attribute):
        """
        Searches and creates attribute term if not found.
        @param attributes_term_data: Data of Attribute values from Woo.
        @param instance: Record of the instance.
        @param woo_attribute: Record of Attribute of Woo layer.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        obj_woo_attribute_term = self.env['woo.product.attribute.term.ept']
        odoo_attribute_value_obj = self.env['product.attribute.value']

        for attribute_term in attributes_term_data:
            woo_attribute_term = obj_woo_attribute_term.search(
                [('woo_attribute_term_id', '=', attribute_term.get('id')), ('exported_in_woo', '=', True),
                 ('woo_instance_id', '=', instance.id)], limit=1)
            if woo_attribute_term:
                woo_attribute_term.write({'count': attribute_term.get('count'),
                                          "description": attribute_term.get("description")})
                continue
            odoo_attribute_value = odoo_attribute_value_obj.get_attribute_values(attribute_term.get('name'),
                                                                                 woo_attribute.attribute_id.id,
                                                                                 auto_create=True)[0]
            woo_attribute_term = obj_woo_attribute_term.search(
                [('attribute_value_id', '=', odoo_attribute_value.id),
                 ('attribute_id', '=', woo_attribute.attribute_id.id),
                 ('woo_attribute_id', '=', woo_attribute.id), ('woo_instance_id', '=', instance.id),
                 ('exported_in_woo', '=', False)], limit=1)
            if woo_attribute_term:
                woo_attribute_term.write({'woo_attribute_term_id': attribute_term.get('id'),
                                          'count': attribute_term.get('count'), 'slug': attribute_term.get('slug'),
                                          'exported_in_woo': True})
            else:
                obj_woo_attribute_term.create({
                    'name': attribute_term.get('name'),
                    'woo_attribute_term_id': attribute_term.get('id'),
                    'slug': attribute_term.get('slug'),
                    "description": attribute_term.get("description"),
                    'woo_instance_id': instance.id,
                    'attribute_value_id': odoo_attribute_value.id,
                    'woo_attribute_id': woo_attribute.woo_attribute_id,
                    'attribute_id': woo_attribute.attribute_id.id,
                    'exported_in_woo': True,
                    'count': attribute_term.get('count')})
        return True

    def sync_woo_attribute_term(self, instance, attribute_ids=False):
        """
         This method is used for send the request in woo and get the response of product attribute Values
         and create that attribute Value into woo commerce connector of odoo
        :return: It will return True if the process is successfully completed.
        @param instance: It contains the browsable object of the current instance
        @param attribute_ids:
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        obj_woo_attribute = self.env['woo.product.attribute.ept']

        wc_api = instance.woo_connect()
        if not attribute_ids:
            woo_attributes = obj_woo_attribute.search([('woo_instance_id', '=', instance.id)])
        else:
            woo_attributes = obj_woo_attribute.search([('woo_instance_id', '=', instance.id),
                                                       ('woo_attribute_id', 'in', attribute_ids)])

        for woo_attribute in woo_attributes:
            try:
                response = wc_api.get("products/attributes/%s/terms" % woo_attribute.woo_attribute_id,
                                      params={'per_page': 100})
            except Exception as error:
                raise UserError(_("Something went wrong while importing Attribute Values.\n\nPlease Check your "
                                  "Connection and Instance Configuration.\n\n" + str(error)))

            attributes_term_data = self.check_woocommerce_response(response, "WooCommerce Attributes Terms",
                                                                   "woo.product.attribute.term.ept", instance)
            if not isinstance(attributes_term_data, list):
                continue

            attributes_term_data += self.import_all_attribute_terms(wc_api, woo_attribute, response, instance)
            self.find_or_create_woo_attribute_term(attributes_term_data, instance, woo_attribute)
        return True

    def woo_import_all_attributes(self, wc_api, response, instance):
        """
        This method is used for get the attribute response as per request by page wise and return it
        @param wc_api: It contains the connection object between odoo and woo
        @return: It will return the response of product attribute into Dict Format.
        @param response:
        @param instance:
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        attributes_data = []
        total_pages = response.headers.get('x-wp-totalpages', 0) if response else 1
        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                try:
                    res = wc_api.get('products/attributes', params={'per_page': 100, 'page': page})
                except Exception as error:
                    raise UserError(_("Something went wrong while importing Attributes.\n\nPlease Check your "
                                      "Connection and Instance Configuration.\n\n" + str(error)))

                data = self.check_woocommerce_response(response, "WooCommerce Attributes", "woo.product.attribute.ept",
                                                       instance)
                if not isinstance(data, list):
                    return []
                attributes_data += data

        return attributes_data

    def find_or_create_woo_attribute(self, attributes_data, instance):
        """
        Searches and creates attribute if not found.
        @param attributes_data: Data of Attributes from Woo.
        @param instance: Record of the instance.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        obj_woo_attribute = self.env['woo.product.attribute.ept']
        odoo_attribute_obj = self.env['product.attribute']

        for attribute in attributes_data:
            woo_attribute = obj_woo_attribute.search([('woo_attribute_id', '=', attribute.get('id')),
                                                      ('woo_instance_id', '=', instance.id),
                                                      ('exported_in_woo', '=', True)], limit=1)
            if woo_attribute:
                continue
            odoo_attribute = odoo_attribute_obj.get_attribute(attribute.get('name'), auto_create=True)[0]
            woo_attribute = obj_woo_attribute.search([('attribute_id', '=', odoo_attribute.id),
                                                      ('woo_instance_id', '=', instance.id),
                                                      ('exported_in_woo', '=', False)], limit=1)
            if woo_attribute:
                woo_attribute.write({
                    'woo_attribute_id': attribute.get('id'), 'order_by': attribute.get('order_by'),
                    'slug': attribute.get('slug'), 'exported_in_woo': True,
                    'has_archives': attribute.get('has_archives')
                })
            else:
                obj_woo_attribute.create({
                    'name': attribute.get('name'), 'woo_attribute_id': attribute.get('id'),
                    'order_by': attribute.get('order_by'), 'slug': attribute.get('slug'),
                    'woo_instance_id': instance.id, 'attribute_id': odoo_attribute.id,
                    'exported_in_woo': True, 'has_archives': attribute.get('has_archives')
                })
        return True

    def sync_woo_attribute(self, instance):
        """
        This method is used for send the request in woo and get the response of product attribute
         and create that attribute into woo commerce connector of odoo
        :param instance: It contains the browsable object of the current instance
        :return: It will return True if the process successfully completed.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        try:
            response = wc_api.get("products/attributes", params={'per_page': 100})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Attributes.\n\nPlease Check your Connection and"
                              "Instance Configuration.\n\n" + str(error)))

        attributes_data = self.check_woocommerce_response(response, "WooCommerce Attributes",
                                                          "woo.product.attribute.ept", instance)
        if isinstance(attributes_data, list):
            attributes_data += self.woo_import_all_attributes(wc_api, response, instance)
            self.find_or_create_woo_attribute(attributes_data, instance)
            self.sync_woo_attribute_term(instance)
        return True

    def import_all_woo_products(self, instance, page, from_date, to_date):
        """
        :param instance: It contains the browsable object of class woo_instance_ept
        :param page: It contains the products page number of woo commerce and its type is Integer
        :param from_date: It contains after create date of product
        :param to_date: It contains before create date of product
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        from_date, to_date = self.woo_product_convert_dates_by_timezone(instance, from_date, to_date)
        if from_date and to_date:
            from_date = str(from_date)[:19].replace(" ", "T")
            to_date = str(to_date)[:19].replace(" ", "T")
        try:
            res = wc_api.get('products', params={'per_page': 100, 'page': page, 'after': from_date, 'before': to_date})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Products.\n\nPlease Check your Connection and"
                              "Instance Configuration.\n\n" + str(error)))

        response = self.check_woocommerce_response(res, "Import Product", "woo.product.template.ept", instance)
        if not isinstance(response, list):
            return []
        return response

    def create_woo_product_queue(self, results, instance, import_all, template_id):
        """
        This method update the data of the product for variations and creates queues of that data.
        @param results: Data of products.
        @param instance: Record of instance.
        @param import_all: Flag for importing all products or not.
        @param template_id: Id of a WooCommerce product, if only needed the data of it and no need of queue.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        bus_bus_obj = self.env['bus.bus']
        process_import_export_obj = self.env["woo.process.import.export"]
        product_queue_ids = []
        woo_process_import_export = process_import_export_obj.browse(self._context.get('import_export_record'))

        total_result = self.process_product_response(results, instance, template_id, import_all)
        if template_id:
            return total_result

        if total_result and not template_id:
            queues = woo_process_import_export.woo_import_products(total_result)
            if queues.queue_line_ids:
                product_queue_ids = queues.mapped('id')
                # message = "Product Queue created ", queues.mapped('name')
                message = "Product Queue created %s" % ', '.join(queues.mapped('name'))
                bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                                     {'title': 'WooCommerce Connector', 'message': message, "sticky": False,
                                      "warning": True})
            self._cr.commit()
        return product_queue_ids

    def get_products_from_woo_v1_v2_v3(self, instance, template_id=False, import_all=False, from_date="", to_date=""):
        """
        This method used to call sub methods related to import products from Woocommerce to Odoo.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        results, total_pages = self.get_templates_from_woo(instance, from_date, to_date, template_id=template_id)
        product_queues = []
        if results:
            if int(total_pages) >= 2:
                product_queues += self.create_woo_product_queue(results, instance, import_all, template_id)
                for page in range(2, int(total_pages) + 1):
                    results = self.import_all_woo_products(instance, page, from_date, to_date)
                    if results:
                        product_queues += self.create_woo_product_queue(results, instance, import_all, template_id)
            else:
                product_queue_ids = self.create_woo_product_queue(results, instance, import_all, template_id)
                if template_id:
                    return product_queue_ids
                product_queues += product_queue_ids
        return product_queues

    def get_templates_from_woo(self, instance, from_date, to_date, template_id):
        """
        This method used to get product templates from Woocommerce to Odoo.
        @param : self, instance, template_id
        @return: results, total_pages
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        from_date, to_date = self.woo_product_convert_dates_by_timezone(instance, from_date, to_date)

        if from_date and to_date:
            from_date = str(from_date)[:19].replace(" ", "T")
            to_date = str(to_date)[:19].replace(" ", "T")
        try:
            if template_id:
                res = wc_api.get('products/%s' % template_id)
            else:
                res = wc_api.get('products', params={'per_page': 100, 'after': from_date, 'before': to_date})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Product.\n\nPlease Check your Connection and"
                              "Instance Configuration.\n\n" + str(error)))

        response = self.check_woocommerce_response(res, "Import Product", "woo.product.template.ept", instance)
        if not isinstance(response, (list, dict)):
            return [], 0

        total_pages = res.headers.get('x-wp-totalpages', 0)
        if template_id:
            results = [response]
        else:
            results = response
        return results, total_pages

    def woo_product_convert_dates_by_timezone(self, instance, from_date, to_date):
        """
        This method converts the dates by timezone of the store to import products.
        @param instance: Instance.
        @param from_date: From date for importing products.
        @param to_date: To date for importing products.
        @author: Meera Sidapara on Date 25-Feb-2022.
        """
        if not from_date:
            if instance.import_products_last_date:
                from_date = instance.import_products_last_date - timedelta(days=1)
            else:
                from_date = fields.Datetime.now() - timedelta(days=1)
        to_date = to_date if to_date else fields.Datetime.now()

        from_date = pytz.utc.localize(from_date).astimezone(pytz.timezone(instance.store_timezone))
        to_date = pytz.utc.localize(to_date).astimezone(pytz.timezone(instance.store_timezone))

        return from_date, to_date

    def check_for_existing_queue(self, product_data_queue_line_ids, woo_id, date_modified):
        """
        This method checks for the existing queue line for the product to create new queue line or not.
        @param product_data_queue_line_ids: Queue lines to check.
        @param woo_id: Id of product.
        @param date_modified: Last modified date of product.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        flag = already_exist_result = False
        already_exist_results = product_data_queue_line_ids.filtered(lambda x: int(x.woo_synced_data_id) == woo_id)
        already_exist_results.sorted(lambda x: x.id, True)

        for already_exist_result in already_exist_results:
            if already_exist_result.woo_update_product_date == date_modified:
                flag = True
                break
            if already_exist_result.state == "draft":
                break
            already_exist_result = False

        return already_exist_result, flag

    def prepare_or_update_woo_product_data(self, results, instance, available_queue, product_data_queue_line_ids):
        """
        This method checks for existing queue lines otherwise
        @param results: Data of products.
        @param instance: Record of instance.
        @param available_queue: True if need to check in queue lines.
        @param product_data_queue_line_ids: Queue lines to check.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        total_results = []

        wc_api = instance.woo_connect()
        for result in results:
            flag = already_exist_result = False
            variants = []
            woo_id = result.get('id')
            date_modified = result.get('date_modified', False)
            # Added the code to skip the product which is already create or available in queue
            if available_queue:
                already_exist_result, flag = self.check_for_existing_queue(product_data_queue_line_ids, woo_id,
                                                                           date_modified)
            if flag:
                continue
            if result.get('variations'):
                variants = self.get_variations_from_woo(result, wc_api, instance)
                if isinstance(variants, str):
                    common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                                   woo_instance_id=instance.id, message=variants,
                                                                   model_name="woo.product.template.ept")
                    continue
            result.update({'variations': variants})
            if already_exist_result:
                already_exist_result.write({'woo_synced_data': json.dumps(result),
                                            'woo_update_product_date': date_modified})
            else:
                total_results.append(result)
        return total_results

    def process_product_response(self, results, instance, template_id=False, import_all=False):
        """
        This method used to get variations from Woocommerce store for uniqe template.
        @param : self,result,wcapi,instance
        @return: variants
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        product_data_queue_obj = self.env['woo.product.data.queue.ept']
        available_queue = product_data_queue_line_ids = False
        if not template_id and not import_all:
            product_data_queues = product_data_queue_obj.search([('woo_instance_id', '=', instance.id)])
            if product_data_queues:
                # available_queue = True
                product_data_queue_line_ids = product_data_queues.queue_line_ids.filtered(
                    lambda x: x.state in ["draft", "done"])
        total_results = self.prepare_or_update_woo_product_data(results, instance, available_queue,
                                                                product_data_queue_line_ids)

        return total_results

    def get_variations_from_woo(self, result, wc_api, instance):
        """
        This method used to get variations from Woocommerce store for unique template.
        @param : self,result,wcapi,instance
        @return: variants
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        try:
            params = {"per_page": 100}
            """This part is not added in the Exception Handling as already handled and it is deep process. If Warning is
            raised here, then whole process will break.
            @note : By Maulik Barad on Date 20-Jan-2021 for Task 170202."""
            response = wc_api.get("products/%s/variations" % (result.get("id")), params=params)
            variants = response.json()

            total_pages = response.headers.get("X-WP-TotalPages")
            if int(total_pages) > 1:
                for page in range(2, int(total_pages) + 1):
                    params["page"] = page
                    response = wc_api.get("products/%s/variations" % (result.get("id")), params=params)
                    variants += response.json()

        except Exception as error:
            message = "Json Error : While Import Product Variants from WooCommerce for instance %s. \n%s" % (
                instance.name, error)
            return message
        return variants

    def search_odoo_product_variant(self, woo_instance, product_sku, variant_id):
        """
        :param woo_instance: It is the browsable object of woo commerce instance
        :param product_sku : It is the default code of product and its type is String
        :param variant_id : It is the id of the product variant and its type is Integer
        :return : It will returns the odoo product and woo product if it is exists
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Modify by Haresh Mori on date 31/12/2019 modification adds active_test=False for searching an archived
        product for a webhook process.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        odoo_product = self.env['product.product']
        woo_product_obj = self.env['woo.product.product.ept']

        woo_product = woo_product_obj.with_context(active_test=False).search(
            [('variant_id', '=', variant_id), ('woo_instance_id', '=', woo_instance.id)], limit=1)

        if not woo_product:
            woo_product = woo_product_obj.with_context(active_test=False).search(
                [('default_code', '=', product_sku),
                 ('woo_template_id.woo_tmpl_id', '=', False),
                 ('woo_instance_id', '=', woo_instance.id)], limit=1)

        if not woo_product:
            woo_product = woo_product_obj.with_context(active_test=False).search(
                [('product_id.default_code', '=', product_sku),
                 ('woo_template_id.woo_tmpl_id', '=', False),
                 ('woo_instance_id', '=', woo_instance.id)], limit=1)

        if not woo_product:
            odoo_product = odoo_product.search([('default_code', '=', product_sku)], limit=1)
        return woo_product, odoo_product

    def prepare_woo_attribute_line_vals(self, attributes_data):
        """
        This method prepares data for the attribute lines to add in Product template.
        @param attributes_data: Data of attributes and values.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        attrib_line_vals = []

        for attrib in attributes_data:
            if not attrib.get('variation'):
                continue
            attrib_name = attrib.get('name')
            attrib_values = attrib.get('options')
            attribute = product_attribute_obj.get_attribute(attrib_name, create_variant='always', auto_create=True)[0]
            attr_val_ids = []

            for attrib_vals in attrib_values:
                attrib_value = product_attribute_value_obj.get_attribute_values(attrib_vals, attribute.id, True)[0]
                attr_val_ids.append(attrib_value.id)

            if attr_val_ids:
                attribute_line_data = [0, 0, {'attribute_id': attribute.id, 'value_ids': [[6, False, attr_val_ids]]}]
                attrib_line_vals.append(attribute_line_data)

        return attrib_line_vals

    def woo_create_variant_product(self, product_template_dict, woo_instance):
        """
        :param product_template_dict: It contains the product template info with variants and its type is Dictionary
        :param woo_instance: It is the browsable object of woo commerce instance
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        product_template_obj = self.env['product.template']

        template_title = ""
        if product_template_dict.get('title'):
            template_title = product_template_dict.get('title')
        elif product_template_dict.get('name'):
            template_title = product_template_dict.get('name')

        attrib_line_vals = self.prepare_woo_attribute_line_vals(product_template_dict.get('attributes'))

        if attrib_line_vals:
            product_template_values = {'name': template_title, 'detailed_type': 'product',
                                       'attribute_line_ids': attrib_line_vals}
            if ir_config_parameter_obj.sudo().get_param("woo_commerce_ept.set_sales_description"):
                product_template_values.update({"description_sale": product_template_dict.get("description", ""),
                                                "description": product_template_dict.get("short_description", "")})

            product_template = product_template_obj.create(product_template_values)
            available_odoo_products = self.woo_set_variant_sku(woo_instance, product_template_dict, product_template,
                                                               woo_instance.sync_price_with_product)
            if available_odoo_products:
                return product_template, available_odoo_products
        return False, False

    @api.model
    def find_template_attribute_values(self, template_attributes, variation_attributes, product_template):
        """
        Finds template's attribute values combination records and prepare domain for searching the odoo product.
        @author: Maulik Barad on Date 06-Dec-2019.
        @param template_attributes: Attributes of Woo template.
        @param variation_attributes: Attributes of Woo product.
        @param product_template: Odoo template.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        template_attribute_value_domain = []
        for variation_attribute in variation_attributes:
            attribute_val = variation_attribute.get('option')
            attribute_name = variation_attribute.get('name')
            for attribute in template_attributes:
                if attribute.get('variation') and \
                        attribute.get('name') and attribute.get('name').replace(" ", "-").lower() == attribute_name:
                    attribute_name = attribute.get('name')
                    break
            product_attribute = self.env["product.attribute"].get_attribute(attribute_name, "radio", "always", True)
            if product_attribute:
                product_attribute_value = self.env["product.attribute.value"].get_attribute_values(attribute_val,
                                                                                                   product_attribute.id,
                                                                                                   auto_create=True)
                if product_attribute_value:
                    template_attribute_value_id = self.env['product.template.attribute.value'].search(
                        [('product_attribute_value_id', '=', product_attribute_value.id),
                         ('attribute_id', '=', product_attribute.id),
                         ('product_tmpl_id', '=', product_template.id)], limit=1)
                    if template_attribute_value_id:
                        domain = ('product_template_attribute_value_ids', '=', template_attribute_value_id.id)
                        template_attribute_value_domain.append(domain)
                    else:
                        return []

        return template_attribute_value_domain

    def set_woo_product_price(self, product_template, pricelist_item, price):
        """
        This method is used to set price of the product.
        @param product_template: Record of the product.
        @param pricelist_item: Record of the pricelist item.
        @param price: Price in WooCommerce.
        @author: Maulik Barad on Date 06-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        if product_template.company_id and pricelist_item.currency_id.id != \
                product_template.company_id.currency_id.id:
            instance_currency = pricelist_item.currency_id
            product_company_currency = product_template.company_id.currency_id
            price = instance_currency.compute(float(price), product_company_currency)
        pricelist_item.write({'fixed_price': price})
        return True

    def woo_set_variant_sku(self, woo_instance, product_template_dict, product_template, sync_price_with_product=False):
        """
        :param woo_instance: It contains the browsable object of the current instance
        :param product_template_dict: It contains the product template info with variants and type is Dictionary
        :param product_template: It is the browsable object of product template
        :param sync_price_with_product: It contains the value od price if it is sync or not with product and Its type
        is Boolean
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        odoo_product_obj = self.env['product.product']
        available_odoo_products = {}
        virtual_product_list = []
        for variation in product_template_dict.get('variations'):
            sku = variation.get('sku')
            woo_weight = float(variation.get("weight") or "0.0")
            variation_attributes = variation.get('attributes')
            virtual_product_list.append(variation.get('virtual', False))
            if len(product_template.attribute_line_ids.ids) != len(variation_attributes):
                continue

            template_attribute_value_domain = self.find_template_attribute_values(
                product_template_dict.get("attributes"), variation_attributes, product_template)

            if template_attribute_value_domain:
                odoo_product = odoo_product_obj.search(template_attribute_value_domain)
                if odoo_product:
                    weight = self.convert_weight_by_uom(woo_weight, woo_instance, import_process=True)
                    odoo_product.write({'default_code': sku, "weight": weight})
                    available_odoo_products.update({variation["id"]: odoo_product})

        if all(virtual_product_list):
            product_template.write({'detailed_type': 'service'})
        if not available_odoo_products:
            product_template.unlink()
        return available_odoo_products

    def sync_woo_categ_with_product_v1_v2_v3(self, instance, woo_categories, sync_images=True):
        """
        :param instance: It is the browsable object of the woo commerce instance
        :param woo_categories: It contains the category details of products and and its type is Dict
        :param sync_images: It contains the either True or False and its type is Boolean
        :return: It will return the category ids into list format
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        obj_woo_product_categ = self.env['woo.product.categ.ept']
        categ_ids = []
        for woo_category in woo_categories:
            woo_product_categ = obj_woo_product_categ.search([('woo_categ_id', '=', woo_category.get('id')),
                                                              ('woo_instance_id', '=', instance.id)], limit=1)
            if not woo_product_categ:
                woo_product_categ = obj_woo_product_categ.search([('slug', '=', woo_category.get('slug')),
                                                                  ('woo_instance_id', '=', instance.id)], limit=1)
            if woo_product_categ:
                woo_product_categ.write({
                    'woo_categ_id': woo_category.get('id'), 'name': woo_category.get('name'),
                    'display': woo_category.get('display'), 'slug': woo_category.get('slug'),
                    'exported_in_woo': True
                })
            else:
                woo_product_categ = obj_woo_product_categ.create({
                    'woo_categ_id': woo_category.get('id'), 'name': woo_category.get('name'),
                    'display': woo_category.get('display'), 'slug': woo_category.get('slug'),
                    'woo_instance_id': instance.id, 'exported_in_woo': True
                })
            obj_woo_product_categ.sync_woo_product_category(instance, woo_product_categ, sync_images)
            categ_ids.append(woo_product_categ.id)
        return categ_ids

    def sync_woo_tags_with_product_v1_v2_v3(self, woo_instance, woo_tags):
        """
        :param woo_instance: It is the browsable object of the woo commerce instance
        :param woo_tags: It contains the tags details of products and and its type is Dict
        :return: It will return the tags ids into list format
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_tags_obj = self.env['woo.tags.ept']
        tag_ids = []
        for woo_tag in woo_tags:
            woo_product_tag = woo_product_tags_obj.search([('woo_tag_id', '=', woo_tag.get('id')),
                                                           ('woo_instance_id', '=', woo_instance.id)], limit=1)
            if not woo_product_tag:
                woo_product_tag = woo_product_tags_obj.search([('slug', '=', woo_tag.get('slug')),
                                                               ('woo_instance_id', '=', woo_instance.id)], limit=1)
            if woo_product_tag:
                woo_product_tag.write({
                    'name': woo_tag.get('name'), 'slug': woo_tag.get('slug'), 'exported_in_woo': True
                })
            else:
                woo_product_tag = woo_product_tags_obj.create({
                    'woo_tag_id': woo_tag.get('id'), 'name': woo_tag.get('name'),
                    'slug': woo_tag.get('slug'), 'woo_instance_id': woo_instance.id,
                    'exported_in_woo': True
                })
            tag_ids.append(woo_product_tag.id)
        return tag_ids

    def is_product_importable(self, result, odoo_product, woo_product):
        """
        :param result: It contains the products detail and its type is Dictionary
        :param odoo_product: It contains the product variant of odoo and its type is object
        :param woo_product: It contains the woo product variant and its type is object
        :return: It will return the message if error is occur
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_skus = []
        importable = True
        message = ""
        variations = result.get('variations')
        title = result.get('title')

        for variation in variations:
            woo_skus.append(variation.get("sku"))
            woo_skus = list(filter(lambda x: len(x) > 0, woo_skus))
            total_woo_sku = len(set(woo_skus))
            if not len(woo_skus) == total_woo_sku:
                duplicate_skus = list(set([woo_sku for woo_sku in woo_skus if woo_skus.count(woo_sku) > 1]))
                message = "Duplicate SKU(%s) found in Product: %s and ID: %s." % (duplicate_skus, title,
                                                                                  result.get("id"))
                importable = False

        if not odoo_product and not woo_product and importable:
            product_attributes = []
            for variation in variations:
                product_attributes.append(variation.get('attributes'))
            if not product_attributes and result.get('type') == 'variable':
                message = "Attributes are not set in variation of Product: %s and ID: %s." % (title, result.get("id"))
                importable = False

        return importable, message

    @api.model
    def prepare_woo_template_vals(self, template_data, odoo_template_id, import_for_order, woo_instance):
        """
        Prepares vals for the woo template.
        @author: Maulik Barad on Date 05-Dec-2019.
        @param template_data: Dictionary of template data.
        @param odoo_template_id:Odoo template id to give relation.
        @param import_for_order: True when importing product while order process.
        @param woo_instance: Instance of Woo.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        if import_for_order:
            woo_category_ids = self.sync_woo_categ_with_product_v1_v2_v3(woo_instance, template_data["woo_categ_ids"],
                                                                         woo_instance.sync_images_with_product)
            woo_tag_ids = self.sync_woo_tags_with_product_v1_v2_v3(woo_instance, template_data["woo_tag_ids"])
        else:
            woo_category_ids = []
            woo_tag_ids = []
            for woo_category in template_data["woo_categ_ids"]:
                woo_categ = self.env["woo.product.categ.ept"].search([("woo_categ_id", "=", woo_category.get("id")),
                                                                      ('woo_instance_id', '=', woo_instance.id)],
                                                                     limit=1).id
                woo_categ and woo_category_ids.append(woo_categ)
            for woo_tag in template_data["woo_tag_ids"]:
                product_tag = self.env["woo.tags.ept"].search([("woo_tag_id", "=", woo_tag.get("id")),
                                                               ('woo_instance_id', '=', woo_instance.id)], limit=1).id
                product_tag and woo_tag_ids.append(product_tag)

        template_data.update({
            "product_tmpl_id": odoo_template_id,
            "exported_in_woo": True,
            "woo_categ_ids": [(6, 0, woo_category_ids)],
            "woo_tag_ids": [(6, 0, woo_tag_ids)]
        })
        return template_data

    def get_existing_images(self, woo_template, woo_product=False):
        """
        This method prepares data of existing images in product for comparison.
        @param woo_product: Record of variant of Woo layer.
        @param woo_template: Record of template of Woo layer.
        @author: Maulik Barad on Date 09-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        existing_common_images = {}
        if woo_product:
            images = woo_product.product_id.ept_image_ids
        else:
            images = woo_template.product_tmpl_id.ept_image_ids

        for odoo_image in images:
            if not odoo_image.image:
                continue
            key = hashlib.md5(odoo_image.image).hexdigest()
            if not key:
                continue
            existing_common_images.update({key: odoo_image.id})
        return existing_common_images

    def find_or_create_common_product_image(self, woo_template, image, url, product_dict={}, woo_product=False):
        """
        This method is used to search or create common product image record, if not available.
        @param woo_template: Record of the template in Woo layer.
        @param image: Image downloaded from WooCommerce.
        @param url: Url of the image.
        @param product_dict: Dict for setting the main image in variant.
        @param woo_product: Record of the product in Woo layer.
        @author: Maulik Barad on Date 09-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_obj = self.env["woo.product.image.ept"]
        common_product_image_obj = common_product_image = self.env["common.product.image.ept"]

        domain = []
        vals = {"name": woo_template.name, "template_id": woo_template.product_tmpl_id.id, "image": image, "url": url}

        if woo_product:
            if not woo_product.product_id.image_1920 or product_dict.get('is_image'):
                woo_product.product_id.image_1920 = image
                common_product_image = woo_product.product_id.ept_image_ids.filtered(
                    lambda x: x.image == woo_product.product_id.image_1920)
            else:
                vals.update({"product_id": woo_product.product_id.id})
            domain.append(("woo_variant_id", "=", woo_product.id))

        if not woo_product and not woo_template.product_tmpl_id.image_1920:
            woo_template.product_tmpl_id.image_1920 = image
            common_product_image = woo_template.product_tmpl_id.ept_image_ids.filtered(
                lambda x: x.image == woo_template.product_tmpl_id.image_1920)
        elif not common_product_image:
            common_product_image = common_product_image_obj.create(vals)

        domain += [("woo_template_id", "=", woo_template.id), ("odoo_image_id", "=", common_product_image.id)]
        woo_product_image = woo_product_image_obj.search(domain)
        return woo_product_image

    def update_woo_template_images(self, template_images, woo_template):
        """
        This method updates the template images.
        @param template_images: Data of images of template.
        @param woo_template: Record of the template in Woo layer.
        @author: Maulik Barad on Date 09-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_obj = woo_product_images = self.env["woo.product.image.ept"]
        existing_common_template_images = self.get_existing_images(woo_template)
        for template_image in template_images:
            image_id = template_image["id"]
            url = template_image.get('src')
            woo_product_image = woo_product_image_obj.search([("woo_template_id", "=", woo_template.id),
                                                              ("woo_variant_id", "=", False),
                                                              ("woo_image_id", "=", image_id)])
            if not woo_product_image:
                try:
                    response = requests.get(url, stream=True, verify=True, timeout=10)
                    if response.status_code == 200:
                        image = base64.b64encode(response.content)
                        key = hashlib.md5(image).hexdigest()
                        if key in existing_common_template_images.keys():
                            woo_product_image = woo_product_image_obj.create({
                                "woo_template_id": woo_template.id,
                                "woo_image_id": image_id, "odoo_image_id": existing_common_template_images[key]})
                        else:
                            woo_product_image = self.find_or_create_common_product_image(woo_template, image, url)
                            if woo_product_image:
                                woo_product_image.woo_image_id = image_id
                except Exception:
                    pass
            woo_product_images += woo_product_image
        return woo_product_images

    def update_woo_variant_image(self, variant_image, woo_template, woo_product, product_dict):
        """
        This method updates the variant image.
        @param variant_image: Data of image of variant.
        @param woo_template: Record of the template in Woo layer.
        @param woo_product: Record of the template in Woo layer.
        @param product_dict: Dict for setting the main image in variant.
        @author: Maulik Barad on Date 09-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_obj = self.env["woo.product.image.ept"]
        image_id = variant_image["id"]
        url = variant_image.get('src')
        existing_common_variant_images = self.get_existing_images(woo_template, woo_product)

        woo_product_image = woo_product_image_obj.search([("woo_variant_id", "=", woo_product.id),
                                                          ("woo_image_id", "=", image_id)])
        if not woo_product_image:
            try:
                response = requests.get(url, stream=True, verify=True, timeout=10)
                if response.status_code == 200:
                    image = base64.b64encode(response.content)
                    key = hashlib.md5(image).hexdigest()
                    if key in existing_common_variant_images.keys():
                        woo_product_image = woo_product_image_obj.create({
                            "woo_template_id": woo_template.id,
                            "woo_variant_id": woo_product.id,
                            "woo_image_id": image_id,
                            "odoo_image_id": existing_common_variant_images[key]})
                    else:
                        woo_product_image = self.find_or_create_common_product_image(woo_template, image, url,
                                                                                     product_dict, woo_product)
                        if woo_product_image:
                            woo_product_image.woo_image_id = image_id
            except Exception:
                pass
        return woo_product_image

    @api.model
    def update_product_images(self, template_images, variant_image, woo_template, woo_product, template_image_updated,
                              product_dict={}):
        """
        Imports/Updates images of Woo template and variant.
        @param template_images: Images data of Woo template.
        @param variant_image: Image data of Woo variant.
        @param woo_template: Template in Woo layer.
        @param woo_product: Variant in Woo layer.
        @param template_image_updated: True when images of template is updated.
        @param product_dict: Dict for setting the main image in variant.
        @author: Maulik Barad on Date 12-Dec-2019.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_obj = need_to_remove = self.env["woo.product.image.ept"]

        if not template_image_updated:
            woo_product_images = self.update_woo_template_images(template_images, woo_template)
            all_woo_product_images = woo_product_image_obj.search([("woo_template_id", "=", woo_template.id),
                                                                   ("woo_variant_id", "=", False)])

            need_to_remove += (all_woo_product_images - woo_product_images)
            _logger.info("Images Updated for Template %s", woo_template.name)
        if variant_image:
            woo_product_image = self.update_woo_variant_image(variant_image, woo_template, woo_product, product_dict)
            all_woo_product_images = woo_product_image_obj.search([("woo_template_id", "=", woo_template.id),
                                                                   ("woo_variant_id", "=", woo_product.id)])

            need_to_remove += (all_woo_product_images - woo_product_image)
        need_to_remove.unlink()
        _logger.info("Images Updated for Variant %s", woo_product.name)
        return True

    @api.model
    def sync_products(self, product_data_queue_lines, woo_instance, skip_existing_products=False,
                      order_queue_line=False):
        """
        This method used to Create/Update products from Woocommerce to Odoo.
        @param : self, product_data_queue_lines, woo_instance, skip_existing_products=False,
        order_queue_line=False
        @return: True
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        queue_counter = 0
        if order_queue_line:
            # self.env["woo.process.import.export"].sync_woo_attributes(woo_instance)
            self.env['woo.product.template.ept'].sync_woo_attribute(woo_instance)
        else:
            order_queue_line = self.env["woo.order.data.queue.line.ept"]

        for product_data_queue_line in product_data_queue_lines:
            if queue_counter == 10:
                if not order_queue_line:
                    product_queue_id = product_data_queue_line.queue_id if product_data_queue_line else False
                    if product_queue_id:
                        product_queue_id.is_process_queue = True
                self._cr.commit()
                queue_counter = 0

            queue_counter += 1
            template_updated = False
            data, product_queue_id, product_data_queue_line, sync_category_and_tags = self.prepare_product_response(
                order_queue_line, product_data_queue_line)
            woo_product_template_id, template_title = data.get("id"), data.get("name")
            if data.get('type') not in ['simple', 'variable', 'bundle', 'grouped', 'external']:
                message = """The default WooCommerce does not support this product type. Product: %s and received
                product type: %s.""" % (template_title, data.get('type'))
                common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                               woo_instance_id=woo_instance.id, model_name=self._name,
                                                               message=message,
                                                               woo_product_queue_line_id=product_data_queue_line.id,
                                                               woo_order_data_queue_line_id=order_queue_line.id)
                _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                             product_queue_id, message)
                product_data_queue_line.write({"state": "failed", "last_process_date": datetime.now()})
                continue
            woo_template = self.with_context(active_test=False).search(
                [("woo_tmpl_id", "=", woo_product_template_id), ("woo_instance_id", "=", woo_instance.id)], limit=1)
            _logger.info("Process started for Product-%s||%s||Queue %s.", woo_product_template_id, template_title,
                         product_queue_id if order_queue_line else product_data_queue_line.queue_id.name)
            if any(isinstance(variant, int) for variant in data["variations"]):
                message = """Process Failed of Product: %s || Reason is the default WooCommerce support 
                only dict type response from product variations.""" % (template_title)
                common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                               woo_instance_id=woo_instance.id, model_name=self._name,
                                                               message=message,
                                                               woo_product_queue_line_id=product_data_queue_line.id,
                                                               woo_order_data_queue_line_id=order_queue_line.id)
                _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                             product_queue_id, message)
                product_data_queue_line.write({"state": "failed", "last_process_date": datetime.now()})
                continue
            if data["variations"]:
                new_woo_template = self.variation_product_sync(woo_instance, data, product_data_queue_line,
                                                               order_queue_line, woo_template, product_queue_id,
                                                               sync_category_and_tags, skip_existing_products)
                if new_woo_template:
                    woo_template = new_woo_template
                else:
                    continue
            if data["type"] == "simple" or data["type"] == "bundle":
                new_woo_template = self.simple_product_sync(woo_instance, data, product_queue_id,
                                                            product_data_queue_line, template_updated,
                                                            skip_existing_products, order_queue_line)
                if not isinstance(new_woo_template, bool):
                    woo_template = new_woo_template
                elif not new_woo_template:
                    continue
            if not order_queue_line:
                if woo_template:
                    # WooCommerce Meta Mapping for import Products
                    woo_operation = 'import_product'
                    meta_mapping_ids = woo_instance.meta_mapping_ids.filtered(
                        lambda meta: meta.woo_operation == woo_operation)
                    product_template = woo_template.product_tmpl_id
                    product_variants = woo_template.woo_product_ids.mapped('product_id')
                    operation_type = "import"
                    if meta_mapping_ids and meta_mapping_ids.filtered(
                            lambda meta: meta.model_id.model == product_template._name):
                        woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(data, operation_type,
                                                                                                  product_template)

                    if meta_mapping_ids and meta_mapping_ids.filtered(
                            lambda meta: meta.model_id.model == product_variants._name):
                        woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(data, operation_type,
                                                                                                  product_variants)
                    product_data_queue_line.write(
                        {"state": "done", "last_process_date": datetime.now()})
                else:
                    message = """Misconfiguration at Woocommerce store for product named - '%s'.
                              - It seems this might be a variation product, but variations are not defined at 
                              store.""" % template_title
                    common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                                   woo_instance_id=woo_instance.id,
                                                                   model_name=self._name, message=message,
                                                                   woo_product_queue_line_id=product_data_queue_line.id)
                    _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                                 product_queue_id, message)
                    product_data_queue_line.write({"state": "failed", "last_process_date": datetime.now()})
                product_data_queue_line.queue_id.is_process_queue = False
            _logger.info("Process done for Product-%s||%s||Queue %s.", woo_product_template_id, template_title,
                         product_queue_id if order_queue_line else product_data_queue_line.queue_id.name)
        return True

    def prepare_product_response(self, order_queue_line, product_data_queue_line):
        """
        This method used Prepare a product response from order data queue or product data queue.
        @param : self,order_queue_line,product_data_queue_line
        @return: data,product_queue_id,sync_category_and_tags
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 24 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        sync_category_and_tags = False
        if order_queue_line or isinstance(product_data_queue_line, dict):
            data = product_data_queue_line
            product_queue_id = "from Order"
            sync_category_and_tags = True
            product_data_queue_line = self.env["woo.product.data.queue.line.ept"]
        else:
            product_queue_id = product_data_queue_line.queue_id.id
            if product_data_queue_line.queue_id.created_by == "webhook":
                sync_category_and_tags = True
            data = json.loads(product_data_queue_line.woo_synced_data)
        return data, product_queue_id, product_data_queue_line, sync_category_and_tags

    def prepare_template_vals(self, woo_instance, product_response):
        """
        This method used Prepare a template vals.
        @param : self,data
        @return: template_info_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        template_info_vals = {
            "name": product_response.get("name"),
            "woo_tmpl_id": product_response.get("id"),
            "woo_instance_id": woo_instance.id,
            "woo_short_description": product_response.get("short_description", ""),
            "woo_description": product_response.get("description", ""),
            "website_published": product_response["status"] == "publish",
            "taxable": product_response["tax_status"] == "taxable",
            "woo_categ_ids": product_response.get("categories"),
            "woo_tag_ids": product_response.get("tags"),
            "total_variants_in_woo": len(product_response["variations"]) if product_response["variations"] else 1,
            "woo_product_type": product_response["type"],
            "active": True
        }
        if product_response.get("date_created"):
            template_info_vals.update({"created_at": product_response.get("date_created").replace("T", " ")})
        if product_response.get("date_modified"):
            template_info_vals.update({"updated_at": product_response.get("date_modified").replace("T", " ")})
        return template_info_vals

    def available_woo_odoo_products(self, woo_instance, woo_template, product_response):
        """
        This method used to prepare a dictionary of available odoo and WooCommerce products.
        @param : self,woo_instance,woo_template,product_response
        @return: available_woo_products,available_odoo_products
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        available_woo_products = {}
        available_odoo_products = {}
        odoo_template = woo_template.product_tmpl_id
        for variant in product_response["variations"]:
            if not variant["sku"]:
                continue
            woo_product, odoo_product = self.search_odoo_product_variant(woo_instance, variant["sku"], variant["id"])
            if woo_product:
                available_woo_products.update({variant["id"]: woo_product})
            if odoo_product:
                available_odoo_products.update({variant["id"]: odoo_product})
                odoo_template = odoo_product.product_tmpl_id
        return available_woo_products, available_odoo_products, odoo_template

    def prepare_woo_variant_vals(self, woo_instance, variant, template_title=""):
        """
        This method used to prepare woo variant vals.
        @param : self,woo_instance,variant,template_title
        @return: available_woo_products,available_odoo_products
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        if not template_title:
            template_title = variant.get("name")
        variant_info = {
            "name": template_title, "default_code": variant.get("sku"),
            "variant_id": variant.get("id"), "woo_instance_id": woo_instance.id,
            "exported_in_woo": True,
            "product_url": variant.get("permalink", ""),
            "woo_is_manage_stock": variant["manage_stock"],
            "active": True
        }
        # As the date_created field will be empty, when product is not published.
        if variant.get("date_created"):
            variant_info.update({"created_at": variant.get("date_created").replace("T", " ")})
        if variant.get("date_modified"):
            variant_info.update({"updated_at": variant.get("date_modified").replace("T", " ")})

        return variant_info

    def template_attribute_process(self, woo_instance, odoo_template, variant, template_title, data,
                                   product_data_queue_line, order_queue_line):
        """
        This method use to create new attribute if customer only add the attribute value otherwise it will create a
        mismatch logs.
        @param :self,woo_instance,odoo_template,variant,template_title,data,product_data_queue_line,order_queue_line
        @return: odoo_product, True
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        if odoo_template.attribute_line_ids:
            # If the new variant has other attribute than available in odoo template, then exception activity will be
            # generated. otherwise it will add new value in current attribute, and will relate with the new odoo
            # variant.
            woo_attribute_ids = []
            odoo_attributes = odoo_template.attribute_line_ids.attribute_id.ids
            for attribute in variant.get("attributes"):
                attribute = self.env["product.attribute"].get_attribute(attribute["name"])
                woo_attribute_ids.append(attribute.id)
            woo_attribute_ids.sort()
            odoo_attributes.sort()
            if odoo_attributes != woo_attribute_ids:
                message = """- Product %s has tried adding a new attribute for sku '%s' in Odoo.
                          - System will not allow adding new attributes to a product.""" % (template_title,
                                                                                            variant.get("sku"))
                common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                               woo_instance_id=woo_instance.id, model_name=self._name,
                                                               message=message,
                                                               woo_product_queue_line_id=product_data_queue_line.id,
                                                               woo_order_data_queue_line_id=order_queue_line.id)
                if not order_queue_line:
                    product_data_queue_line.state = "failed"
                if woo_instance.is_create_schedule_activity:
                    common_log_line_obj.create_woo_schedule_activity()
                return False

            template_attribute_value_domain = self.find_template_attribute_values(data.get("attributes"),
                                                                                  variant.get("attributes"),
                                                                                  odoo_template)
            if not template_attribute_value_domain:
                for woo_attribute in variant.get("attributes"):
                    attribute_id = self.env["product.attribute"].get_attribute(woo_attribute["name"], auto_create=True)
                    value_id = self.env["product.attribute.value"].get_attribute_values(woo_attribute["option"],
                                                                                        attribute_id.id, True)
                    attribute_line = odoo_template.attribute_line_ids.filtered(
                        lambda x: x.attribute_id.id == attribute_id.id)
                    if value_id.id not in attribute_line.value_ids.ids:
                        attribute_line.value_ids = [(4, value_id.id, False)]
                odoo_template._create_variant_ids()
                template_attribute_value_domain = self.find_template_attribute_values(data.get("attributes"),
                                                                                      variant.get("attributes"),
                                                                                      odoo_template)
            odoo_product = self.env["product.product"].search(template_attribute_value_domain)
            if not odoo_product.default_code:
                odoo_product.default_code = variant["sku"]
            return odoo_product

        template_vals = {"name": template_title, "detailed_type": "product", "default_code": variant["sku"]}
        if self.env["ir.config_parameter"].sudo().get_param("woo_commerce_ept.set_sales_description"):
            template_vals.update({"description_sale": variant.get("description", "")})

        odoo_product = self.env["product.product"].create(template_vals)
        return odoo_product

    def variation_product_sync(self, woo_instance, product_response, product_data_queue_line, order_queue_line,
                               woo_template, product_queue_id, sync_category_and_tags, skip_existing_products):
        """
        This method use to create variation product.
        @param :self,woo_instance,product_response,product_data_queue_line,order_queue_line,
                woo_template,product_queue_id,sync_category_and_tags,template_info,skip_existing_products
        @return: woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 24 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        template_title = product_response.get("name")
        woo_product_template_id = product_response.get("id")
        template_images_updated = False
        template_updated = False
        product_dict = {}

        template_info = self.prepare_template_vals(woo_instance, product_response)
        available_woo_products, available_odoo_products, odoo_template = self.available_woo_odoo_products(
            woo_instance, woo_template, product_response)

        for variant in product_response["variations"]:
            variant_id = variant.get("id")
            product_sku = variant.get("sku")
            variant_price = variant.get("regular_price") or 0.0
            variant_sale_price = variant.get("sale_price") or 0.0
            woo_product = available_woo_products.get(variant_id)
            odoo_product = False
            if woo_product:
                odoo_product = woo_product.product_id
                if skip_existing_products:
                    continue
            is_importable, message = self.is_product_importable(product_response, odoo_product, woo_product)
            if not is_importable:
                common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                               woo_instance_id=woo_instance.id, model_name=self._name,
                                                               message=message,
                                                               woo_product_queue_line_id=product_data_queue_line.id,
                                                               woo_order_data_queue_line_id=order_queue_line.id)
                _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                             product_queue_id, message)
                if not order_queue_line:
                    product_data_queue_line.state = "failed"
                break
            if not product_sku:
                message = "No SKU found for a Variant of {0}.".format(template_title)
                common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                               woo_instance_id=woo_instance.id, model_name=self._name,
                                                               message=message,
                                                               woo_product_queue_line_id=product_data_queue_line.id,
                                                               woo_order_data_queue_line_id=order_queue_line.id)
                _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                             product_queue_id, message)
                continue
            variant_info = self.prepare_woo_variant_vals(woo_instance, variant, template_title)
            if not woo_product:
                if not woo_template:
                    if not odoo_template and woo_instance.auto_import_product:
                        odoo_template, available_odoo_products = self.woo_create_variant_product(
                            product_response, woo_instance)
                    if not odoo_template:
                        message = "%s Template Not found for sku %s in Odoo." % (template_title, product_sku)
                        common_log_line_obj.create_common_log_line_ept(
                            operation_type="import", module="woocommerce_ept", woo_instance_id=woo_instance.id,
                            model_name=self._name, message=message,
                            woo_product_queue_line_id=product_data_queue_line.id,
                            woo_order_data_queue_line_id=order_queue_line.id)
                        _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                                     product_queue_id, message)
                        if not order_queue_line:
                            product_data_queue_line.state = "failed"
                        break

                    woo_template_vals = self.prepare_woo_template_vals(template_info, odoo_template.id,
                                                                       sync_category_and_tags, woo_instance)
                    if odoo_template.detailed_type == 'service':
                        woo_template_vals.update({'is_virtual_product': True})
                    woo_template = self.create(woo_template_vals)
                elif not template_updated:
                    woo_template_vals = self.prepare_woo_template_vals(template_info, odoo_template.id,
                                                                       sync_category_and_tags, woo_instance)
                    woo_template.write(woo_template_vals)
                template_updated = True

                odoo_product = available_odoo_products.get(variant_id)
                if not odoo_product:
                    if not woo_instance.auto_import_product:
                        message = "Product %s Not found for sku %s in Odoo." % (template_title, product_sku)
                        common_log_line_obj.create_common_log_line_ept(
                            operation_type="import", module="woocommerce_ept", woo_instance_id=woo_instance.id,
                            model_name=self._name, message=message,
                            woo_product_queue_line_id=product_data_queue_line.id,
                            woo_order_data_queue_line_id=order_queue_line.id)
                        _logger.info("Product {0} Not found for sku {1} of Queue {2} in Odoo.".format(
                            template_title, product_sku, product_queue_id))
                        if not order_queue_line:
                            product_data_queue_line.state = "failed"
                        continue
                    new_odoo_product = self.template_attribute_process(woo_instance, odoo_template, variant,
                                                                       template_title, product_response,
                                                                       product_data_queue_line, order_queue_line)
                    if not isinstance(new_odoo_product, bool):
                        odoo_product = new_odoo_product
                    elif not new_odoo_product:
                        woo_template = False
                        break

                variant_info.update({"product_id": odoo_product.id,
                                     "woo_template_id": woo_template.id})
                woo_product = self.env["woo.product.product.ept"].create(variant_info)
            else:
                if not woo_template and woo_product:
                    woo_template = woo_product.woo_template_id
                if not template_updated:
                    woo_template_vals = self.prepare_woo_template_vals(template_info,
                                                                       woo_product.product_id.product_tmpl_id.id,
                                                                       sync_category_and_tags, woo_instance)
                    woo_template.write(woo_template_vals)
                    template_updated = True
                woo_product.write(variant_info)
                woo_weight = float(variant.get("weight") or "0.0")
                weight = self.convert_weight_by_uom(woo_weight, woo_instance, import_process=True)
                odoo_product.write({"weight": weight})
            update_price = woo_instance.sync_price_with_product
            update_images = woo_instance.sync_images_with_product
            if update_price:
                woo_instance.woo_pricelist_id.set_product_price_ept(woo_product.product_id.id, variant_price)
                if woo_instance.woo_extra_pricelist_id:
                    woo_instance.woo_extra_pricelist_id.set_product_price_ept(woo_product.product_id.id,
                                                                              variant_sale_price)
            if update_images and isinstance(product_queue_id, str) and product_queue_id == 'from Order':
                if not woo_template.product_tmpl_id.image_1920:
                    product_dict.update(
                        {'product_tmpl_id': woo_template.product_tmpl_id, 'is_image': True})
                self.update_product_images(product_response["images"], variant["image"], woo_template, woo_product,
                                           template_images_updated, product_dict)
                template_images_updated = True
        return woo_template

    def simple_product_sync(self, woo_instance, product_response, product_queue_id, product_data_queue_line,
                            template_updated, skip_existing_products, order_queue_line):
        """
        This method use to create or update a simple products.
        @param :self, woo_instance, product_response, template_info, product_queue_id,
        product_data_queue_line, template_updated, skip_existing_products, order_queue_line
        @return: True, Woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 22 August 2020.
        Task_id:165892
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        woo_template = odoo_template = sync_category_and_tags = False
        update_price = woo_instance.sync_price_with_product
        update_images = woo_instance.sync_images_with_product
        template_title = product_response.get("name")
        woo_product_template_id = product_response.get("id")
        product_sku = product_response["sku"]
        variant_price = product_response.get("regular_price") or 0.0
        variant_sale_price = product_response.get("sale_price") or 0.0
        template_info = self.prepare_template_vals(woo_instance, product_response)

        if order_queue_line:
            sync_category_and_tags = True
        if not product_sku:
            message = """Value of SKU/Internal Reference is not set for product '%s', in the Woocommerce store.""" % \
                      template_title
            common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                           woo_instance_id=woo_instance.id, model_name=self._name,
                                                           message=message,
                                                           woo_product_queue_line_id=product_data_queue_line.id,
                                                           woo_order_data_queue_line_id=order_queue_line.id)
            _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                         product_queue_id, message)
            if not order_queue_line:
                product_data_queue_line.write({"state": "failed", "last_process_date": datetime.now()})
            return False

        woo_product, odoo_product = self.search_odoo_product_variant(woo_instance, product_sku, woo_product_template_id)

        if woo_product and not odoo_product:
            woo_template = woo_product.woo_template_id
            odoo_product = woo_product.product_id
            if skip_existing_products:
                product_data_queue_line.state = "done"
                return False

        if odoo_product:
            odoo_template = odoo_product.product_tmpl_id

        is_importable, message = self.is_product_importable(product_response, odoo_product, woo_product)
        if not is_importable:
            common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                           woo_instance_id=woo_instance.id, model_name=self._name,
                                                           message=message,
                                                           woo_product_queue_line_id=product_data_queue_line.id,
                                                           woo_order_data_queue_line_id=order_queue_line.id)
            _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                         product_queue_id, message)
            if not order_queue_line:
                product_data_queue_line.state = "failed"
            return False
        variant_info = self.prepare_woo_variant_vals(woo_instance, product_response)
        if not woo_product:
            if not woo_template:
                if not odoo_template and woo_instance.auto_import_product:
                    woo_weight = float(product_response.get("weight") or "0.0")
                    weight = self.convert_weight_by_uom(woo_weight, woo_instance, import_process=True)
                    template_vals = {
                        "name": template_title, "detailed_type": "product", "default_code": product_response["sku"],
                        "weight": weight
                    }
                    if self.env["ir.config_parameter"].sudo().get_param("woo_commerce_ept.set_sales_description"):
                        template_vals.update({"description_sale": product_response.get("description", ""),
                                              "description": product_response.get("short_description", "")})
                    if product_response["virtual"]:
                        template_vals.update({"detailed_type": "service"})
                    if woo_instance.woo_instance_product_categ_id:
                        template_vals.update({"categ_id": woo_instance.woo_instance_product_categ_id.id})
                    odoo_template = self.env["product.template"].create(template_vals)
                    odoo_product = odoo_template.product_variant_ids
                if not odoo_template:
                    message = "%s Template Not found for sku %s in Odoo." % (template_title, product_sku)
                    common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                                   woo_instance_id=woo_instance.id,
                                                                   model_name=self._name,
                                                                   message=message,
                                                                   woo_product_queue_line_id=product_data_queue_line.id,
                                                                   woo_order_data_queue_line_id=order_queue_line.id)
                    _logger.info("Process Failed of Product %s||Queue %s||Reason is %s", woo_product_template_id,
                                 product_queue_id, message)
                    if not order_queue_line:
                        product_data_queue_line.state = "failed"
                    return False

                woo_template_vals = self.prepare_woo_template_vals(template_info, odoo_template.id,
                                                                   sync_category_and_tags, woo_instance)
                if product_response["virtual"] and odoo_template.detailed_type == 'service':
                    woo_template_vals.update({"is_virtual_product": True})
                    odoo_template.write({"detailed_type": "service"})
                woo_template = self.create(woo_template_vals)

            variant_info.update({"product_id": odoo_product.id, "woo_template_id": woo_template.id})
            woo_product = self.env["woo.product.product.ept"].create(variant_info)
        else:
            if not template_updated:
                woo_template_vals = self.prepare_woo_template_vals(template_info, woo_template.product_tmpl_id.id,
                                                                   sync_category_and_tags, woo_instance)
                woo_template.write(woo_template_vals)
            woo_product.write(variant_info)
            woo_weight = float(product_response.get("weight") or "0.0")
            weight = self.convert_weight_by_uom(woo_weight, woo_instance, import_process=True)
            odoo_product.write({"weight": weight})
        if update_price:
            woo_instance.woo_pricelist_id.set_product_price_ept(woo_product.product_id.id, variant_price)
            if woo_instance.woo_extra_pricelist_id:
                woo_instance.woo_extra_pricelist_id.set_product_price_ept(woo_product.product_id.id, variant_sale_price)
        if update_images and isinstance(product_queue_id, str) and product_queue_id == 'from Order':
            self.update_product_images(product_response["images"], {}, woo_template, woo_product, False)
        if woo_template:
            return woo_template
        return True

    @api.model
    def update_products_in_woo(self, instance, templates, update_price, publish, update_image,
                               update_basic_detail):
        """
         This method is used for update the product data in woo commerce
        :param instance: It contains the browsable object of the current instance
        :param templates: It contains the browsable object of the woo product template
        :param update_price: It contains either True or False and its type is Boolean
        :param publish: It contains either True or False and its type is Boolean
        :param update_image: It contains either True or False and its type is Boolean
        :param update_basic_detail: It contains either True or False and its type is Boolean
        :return: It will return True if the product update process is successfully completed
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        wc_api = instance.woo_connect()

        if not instance.is_export_update_images:
            update_image = False
        batches = []

        # woo_template_ids = self.check_available_products_in_woocommerce(wc_api, instance)
        # if woo_template_ids:
        #     templates = templates.filtered(lambda woo_template: woo_template.id in woo_template_ids.ids)

        if len(templates) > 100:
            batches += self.browse(self.prepare_batches(templates.ids))
        else:
            batches.append(templates)

        for templates in batches:
            batch_update = {'update': []}
            batch_update_data = []

            for template in templates:
                data = {'id': template.woo_tmpl_id, 'variations': [], "type": template.woo_product_type}
                if publish:
                    data.update({'status': 'publish' if publish == "publish" else 'draft'})
                else:
                    data.update({'status': 'publish' if template.website_published else 'draft'})

                flag, data = self.prepare_product_update_data(template, update_image, update_basic_detail, data)

                data, flag = self.prepare_product_variant_dict(instance, template, data,
                                                               update_basic_detail,
                                                               update_price, update_image)
                flag and batch_update_data.append(data)
            if batch_update_data:
                _logger.info("Start the woo template batch for update")
                batch_update.update({'update': batch_update_data})
                try:
                    res = wc_api.post('products/batch', batch_update)
                except Exception as error:
                    raise UserError(_("Something went wrong while Updating Products.\n\nPlease Check your Connection "
                                      "and Instance Configuration.\n\n" + str(error)))

                response = self.check_woocommerce_response(res, "Update Product", self._name, instance)
                if not isinstance(response, dict):
                    continue
                if response.get('data', {}) and response.get('data', {}).get('status') != 200:
                    message = "Update Product \n%s" % (response.get('message'))
                    common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                                   woo_instance_id=instance.id, model_name=self._name,
                                                                   message=message)
                    continue
                if publish == 'publish':
                    templates.write({'website_published': True})
                elif publish == 'unpublish':
                    templates.write({'website_published': False})
                for product in response.get("update"):
                    if product.get("error"):
                        message = "Update Product \n%s" % (product.get("error").get('message'))
                        common_log_line_obj.create_common_log_line_ept(
                            operation_type="export", module="woocommerce_ept", woo_instance_id=instance.id,
                            model_name=self._name, message=message)
                _logger.info("End the woo template batch for update")
        return True

    def check_available_products_in_woocommerce(self, wc_api, instance):
        """
        This method is used to check product is available in WooCommerce store.
        @param wc_api:
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 06/06/2022.
        """
        results = wc_api.get('products', params={'_fields': 'id', 'per_page': 100})
        data_dict = results.json()
        total_pages = results.headers.get('x-wp-totalpages', 0)
        if results.status_code in [200, 201]:
            page = 2
            while int(total_pages) >= 2:
                results = wc_api.get('products',
                                     params={'_fields': 'id', 'per_page': 100,
                                             'page': page})
                data_dict += results.json()
                if page == int(total_pages):
                    break
                page += 1

        available_product_ids = [str(data.get('id')) for data in data_dict]
        _logger.info('Available products ----------- %s', available_product_ids)
        woo_template_ids = self.env['woo.product.template.ept'].search(
            [('exported_in_woo', '=', True), ('woo_instance_id', '=', instance.id)])
        layer_templates = woo_template_ids.filtered(lambda template: template.woo_tmpl_id not in available_product_ids)
        _logger.info('Layer Template ======================= %s', layer_templates)
        template_ids = woo_template_ids.filtered(lambda template: template.id not in layer_templates.ids)
        if layer_templates:
            layer_templates.unlink()
        return template_ids

    def auto_update_stock(self, ctx):
        """
        This method is call when auto import stock cron in enable
        This method is call update_stock() method which is responsible to update stock in WooCommerce.
        :return: Boolean
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 16-11-2019.
        :Task id: 156886
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_instance_id = ctx.get('woo_instance_id', False)
        instance = self.woo_instance_id.browse(woo_instance_id)
        if instance:
            self.update_stock(instance, instance.last_inventory_update_time)

        return True

    def update_stock(self, instance, export_stock_from_date):
        """
        This method is used for export stock from Odoo to WooCommerce according to stock move.
        @parameter : self, instance, export_stock_from_date
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 16-11-2019.
        :Task id: 156886
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        product_obj = self.env['product.product']
        woo_product_product_obj = self.env['woo.product.product.ept']

        if not export_stock_from_date:
            export_stock_from_date = datetime.now() - timedelta(30)
        odoo_products = product_obj.get_products_based_on_movement_date_ept(export_stock_from_date,
                                                                            instance.company_id)
        instance.last_inventory_update_time = datetime.now()
        woo_templates = woo_product_product_obj.search([('product_id', 'in', odoo_products),
                                                        ('woo_is_manage_stock', '=', True)]).woo_template_id
        woo_templates = woo_templates.filtered(lambda x: x.woo_instance_id == instance and x.exported_in_woo)
        if woo_templates:
            queues = self.with_context(updated_products_in_inventory=odoo_products).woo_create_queue_for_export_stock(
                instance, woo_templates)
        else:
            _logger.info("There is no product movement found between date time from: '%s'  to '%s' for export stock.",
                         export_stock_from_date, datetime.now())
            queues = False
        return queues

    @api.model
    def get_gallery_images(self, instance, woo_template, template):
        tmpl_images = []
        position = 0
        gallery_img_keys = {}
        gallery_images = woo_template.woo_image_ids.filtered(lambda x: not x.woo_variant_id)
        for br_gallery_image in gallery_images:
            image_id = br_gallery_image.woo_image_id
            if br_gallery_image.image and not image_id:
                key = hashlib.md5(br_gallery_image.image).hexdigest()
                if not key:
                    continue
                if key in gallery_img_keys:
                    continue
                gallery_img_keys.update({key: br_gallery_image.id})
                res = img_file_upload.upload_image(instance, br_gallery_image.image,
                                                   "%s_%s_%s" % (
                                                       template.name, template.categ_id.name,
                                                       template.id), br_gallery_image.image_mime_type)
                image_id = res and res.get('id', False) or ''
            if image_id:
                tmpl_images.append({'id': image_id, 'position': position})
                position += 1
                br_gallery_image.woo_image_id = image_id
        return tmpl_images

    def export_product_attributes_in_woo(self, instance, attribute):
        """
        This method is called when attribute type is select
        Find the existing product attribute if it is available then return It else create a new
        product attribute in woo commerce and get response and based on this response create
        that attribute and its value in the woo commerce connector of odoo and return attribute id
        in Dict Format
        :param instance: It contains the browsable object of the current instance
        :param attribute: It contains the product attribute
        :return: It will return the attribute id into Dict Format.
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        wc_api = instance.woo_connect()
        obj_woo_attribute = self.env['woo.product.attribute.ept']
        woo_attribute = obj_woo_attribute.search([('attribute_id', '=', attribute.id),
                                                  ('woo_instance_id', '=', instance.id),
                                                  ('exported_in_woo', '=', True)], limit=1)
        if woo_attribute and woo_attribute.woo_attribute_id:
            return {attribute.id: woo_attribute.woo_attribute_id}
        attribute_name = attribute.with_context(lang=instance.woo_lang_id.code).name
        attribute_data = {
            'name': attribute_name,
            'type': 'select',
        }
        try:
            attribute_res = wc_api.post("products/attributes", attribute_data)
        except Exception as error:
            raise UserError(_("Something went wrong while Exporting Attributes.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        if not isinstance(attribute_res, requests.models.Response):
            message = "Export Product Attributes \nResponse is not in proper format :: %s" % attribute_res
            common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=message)
            return False
        if attribute_res.status_code == 400:
            self.sync_woo_attribute(instance)
            woo_attribute = obj_woo_attribute.search(
                [('attribute_id', '=', attribute.id), ('woo_instance_id', '=', instance.id),
                 ('exported_in_woo', '=', True)], limit=1)
            # If same attribute available in Odoo with different Variants Creation Mode
            # this time it will search in Odoo attribute with same name(For Handle Json Serializable error).
            if not woo_attribute:
                odoo_attributes = self.env['product.attribute'].search([('name', '=', attribute.name)])
                woo_attribute = obj_woo_attribute.search(
                    [('attribute_id', 'in', odoo_attributes.ids), ('woo_instance_id', '=', instance.id),
                     ('exported_in_woo', '=', True)], limit=1)
            if woo_attribute and woo_attribute.woo_attribute_id:
                return {attribute.id: woo_attribute.woo_attribute_id}
        if attribute_res.status_code not in [200, 201]:
            common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=attribute_res.content)
            return False
        attribute_response = attribute_res.json()
        woo_attribute_id = attribute_response.get('id')
        obj_woo_attribute.create({
            'name': attribute and attribute_name or attribute_response.get('name'),
            'woo_attribute_id': woo_attribute_id,
            'order_by': attribute_response.get('order_by'),
            'slug': attribute_response.get('slug'), 'woo_instance_id': instance.id,
            'attribute_id': attribute.id,
            'exported_in_woo': True, 'has_archives': attribute_response.get('has_archives')
        })
        return {attribute.id: woo_attribute_id}

    @api.model
    def get_product_attribute(self, template, instance):
        """
        :param template: It contains the browsable object of the product template
        :param instance: It contains the browsable object of the current instance
        :return: It will return the attributes and Its type is List of Dictionary and return True
                or False for is_variable field
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        position = 0
        is_variable = False
        attributes = []
        for attribute_line in template.attribute_line_ids:
            options = []
            for option in attribute_line.value_ids:
                option_name = option.with_context(lang=instance.woo_lang_id.code).name
                options.append(option_name)
            variation = False
            if attribute_line.attribute_id.create_variant in ['always', 'dynamic']:
                variation = True
            attribute_name = attribute_line.attribute_id.with_context(lang=instance.woo_lang_id.code).name
            attribute_data = {
                'name': attribute_name, 'slug': attribute_line.attribute_id.name.lower(),
                'position': position, 'visible': True, 'variation': variation, 'options': options
            }
            if instance.woo_attribute_type == 'select':
                attrib_data = self.export_product_attributes_in_woo(instance, attribute_line.attribute_id)
                if not attrib_data:
                    break
                attribute_data.update({'id': attrib_data.get(attribute_line.attribute_id.id)})
            elif instance.woo_attribute_type == 'text':
                attribute_data.update({'name': attribute_name})
            position += 1
            if attribute_line.attribute_id.create_variant in ['always', 'dynamic']:
                is_variable = True
            attributes.append(attribute_data)
        return attributes, is_variable

    def prepare_product_variant_dict(self, instance, template, data, basic_detail, update_price, update_image):
        """
        This method is used for prepare the product variant dict based on parameters.
        Maulik : Updates variant in this method. Creates new variant, if not exported in woo.
                 Also updating the attributes in template for the new variant.
        :param instance: It contains the browsable object of the current instance.
        :param template: It contains the woo product template
        :param data: It contains the basic detail of woo product template and Its type is Dict
        :param basic_detail: It contains Either True or False and its type is Boolean
        :param update_price: It contains Either True or False and its type is Boolean
        :param update_image: It contains Either True or False and its type is Boolean
        :return: It will return the updated data dictionary
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        wc_api = instance.woo_connect()
        variants_to_create = []
        flag = True
        for variant in template.woo_product_ids:
            price = 0.0
            sale_price = 0.0
            sale_price_rule = False
            if variant.variant_id:
                info = {'id': variant.variant_id}

                if basic_detail:
                    weight = self.convert_weight_by_uom(variant.product_id.weight, instance)
                    info.update({'sku': variant.default_code, 'weight': str(weight),
                                 "manage_stock": variant.woo_is_manage_stock})
            else:
                attributes = self.get_product_attribute(template.product_tmpl_id, instance)[0]
                info = self.get_variant_data(variant, instance, False)

            if update_image:
                info.update(self.get_variant_image(instance, variant))

            if update_price:
                # price = instance.woo_pricelist_id._get_product_price(variant.product_id, 1.0,
                #                                                      uom=variant.product_id.uom_id)
                # sale_price = instance.woo_extra_pricelist_id._get_product_price(
                #     variant.product_id, 1.0,
                #     uom_id=variant.product_id.uom_id) if instance.woo_extra_pricelist_id else sale_price
                price, regular_price_rule = instance.woo_pricelist_id.get_product_price_list_rule(variant.product_id,
                                                                                                  1.0,
                                                                                                  partner=False)
                info.update({'regular_price': str(price)})
                if instance.woo_extra_pricelist_id:
                    sale_price, sale_price_rule = instance.woo_extra_pricelist_id.get_product_price_list_rule(
                        variant.product_id,
                        1.0,
                        partner=False)
                    if sale_price_rule:
                        info.update({'sale_price': str(sale_price) if sale_price > 0 else ""})

            if template.woo_tmpl_id != variant.variant_id:
                if variant.variant_id:
                    data.get('variations').append(info)
                else:
                    variants_to_create.append(info)
                flag = True
            elif template.woo_tmpl_id == variant.variant_id:
                if data.get('variations', []):
                    del data['variations']
                if basic_detail:
                    data.update({'sku': variant.default_code, "manage_stock": variant.woo_is_manage_stock})
                if update_price:
                    data.update({'regular_price': str(price)})
                    if instance.woo_extra_pricelist_id and sale_price_rule:
                        data.update({'sale_price': str(sale_price) if sale_price > 0 else ""})
                flag = True

        if data.get('variations'):
            variant_batches = self.prepare_batches(data.get('variations'))
            for woo_variants in variant_batches:
                _logger.info('variations batch processing')
                try:
                    res = wc_api.post('products/%s/variations/batch' % (data.get('id')), {'update': woo_variants})
                except Exception as error:
                    raise UserError(_("Something went wrong while Updating Variants.\n\nPlease Check your Connection "
                                      "and Instance Configuration.\n\n" + str(error)))
                _logger.info('variations batch process completed [status: %s]', res.status_code)
                if res.status_code in [200, 201]:
                    if data.get("variations"):
                        del data['variations']
                if res.status_code not in [200, 201]:
                    message = "Update Product Variations\n%s" % res.content
                    common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                                   woo_instance_id=instance.id, model_name=self._name,
                                                                   message=message)
        if variants_to_create:
            """Needed to update the attributes of template for adding new variant, while update process."""
            _logger.info("Updating attributes of %s in Woo.." % template.name)
            if data.get("variations"):
                del data['variations']
            data.update({"attributes": attributes})
            try:
                wc_api.put("products/%s" % (data.get("id")), data)
            except Exception as error:
                raise UserError(_("Something went wrong while Updating product.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            _logger.info("Creating variants in Woo..")
            try:
                res = wc_api.post('products/%s/variations/batch' % (data.get('id')), {'create': variants_to_create})
            except Exception as error:
                raise UserError(_("Something went wrong while Creating Variants.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))
            try:
                response = res.json()
            except Exception as error:
                message = "Json Error : While update products to WooCommerce for instance %s. \n%s" % (
                    instance.name, error)
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, model_name=self._name,
                                                               message=message)
                return data, flag
            for product in response.get("create"):
                if product.get("error"):
                    message = "Update Product \n%s" % (product.get("error").get('message'))
                    common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                                   woo_instance_id=instance.id, model_name=self._name,
                                                                   message=message)
                else:
                    variant_id = product.get("id")
                    variant = template.woo_product_ids.filtered(lambda x: x.default_code == product.get("sku"))
                    if variant:
                        variant.write({"variant_id": variant_id, "exported_in_woo": True})

            self.sync_woo_attribute_term(instance)

        return data, flag

    def prepare_product_update_data(self, template, update_image, update_basic_detail, data):
        """
         This method is used for prepare the products details into Dictionary based on parameters
        :param template: It contains the woo product template
        :param update_image: It contains Either True or False and its type is Boolean
        :param update_basic_detail: It contains Either True or False and its type is Boolean
        :param data: It contains the basic detail of woo product template and Its type is Dict
        :return: It will return the updated product dictionary
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        instance = template.woo_instance_id
        flag = False
        tmpl_images = []
        if update_image:
            tmpl_images += self.get_gallery_images(instance, template, template.product_tmpl_id)
            data.update({"images": tmpl_images})
            flag = True

        if update_basic_detail:
            weight = self.convert_weight_by_uom(template.product_tmpl_id.weight, instance)
            name = template.with_context(lang=instance.woo_lang_id.code).name
            description = template.with_context(lang=instance.woo_lang_id.code).woo_description
            short_description = template.with_context(lang=instance.woo_lang_id.code).woo_short_description

            data.update({
                'name': name,
                'enable_html_description': True,
                'enable_html_short_description': True, 'description': description,
                'short_description': short_description,
                'weight': str(weight),
                'taxable': template.taxable and 'true' or 'false'
            })
            data = template.add_woo_category_and_tags(data)

        return flag, data

    @api.model
    def export_products_in_woo(self, instance, woo_templates, update_price, publish, update_image, basic_detail):
        """
        :param instance: It contains the browsable object of the current instance
        :param woo_templates: It contains the browsable object of the woo product templates
        :param update_price: It contains either True or False and its type is Boolean
        :param publish: It contains either True or False and its type is Boolean
        :param update_image: It contains either True or False and its type is Boolean
        :param basic_detail: It contains either True or False and its type is Boolean
        :return: It will return the True if the process is successfully complete
         @author: Dipak Gogiya @Emipro Technologies Pvt.Ltd
         Migrated Maulik Barad on Date 07-Oct-2021.
        """
        start = time.time()
        wc_api = instance.woo_connect()
        common_log_line_obj = self.env['common.log.lines.ept']
        if not instance.is_export_update_images:
            update_image = False
        for woo_template in woo_templates:
            _logger.info("Start the export woo product: '%s'", woo_template.name)
            data = self.prepare_product_data(woo_template, publish, update_price, update_image, basic_detail)
            variants = data.get('variations') or []
            data.update({'variations': []})

            response = self.export_woo_template(woo_template, data)
            if not response:
                continue
            response_variations = []
            woo_tmpl_id = response.get('id')

            if woo_tmpl_id and variants:
                response_variations = self.export_woo_variants(variants, woo_tmpl_id, wc_api, woo_template)

            self.woo_update_template_variant_data(response_variations, woo_template, response, woo_tmpl_id, publish)
            if instance.woo_attribute_type == 'select':
                attribute_ids = []
                for variant in variants:
                    for attribute in variant.get('attributes'):
                        attribute_ids.append(int(attribute.get('id')))
                self.sync_woo_attribute_term(instance, list(set(attribute_ids)))

            _logger.info("End the export woo product: '%s' process", woo_template.name)
            self._cr.commit()
        end = time.time()
        _logger.info("Exported %s templates in %s seconds.", len(woo_templates), str(end - start))
        return True

    def add_woo_category_and_tags(self, data):
        """
        This method updates data dict with category and tags for exporting products.
        @param data: Dictionary of product data.
        @author: Maulik Barad on Date 12-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_categ_ids = list(map(int, self.woo_categ_ids.mapped("woo_categ_id")))
        if all(woo_categ_ids):
            categ_ids = [{'id': cat_id} for cat_id in woo_categ_ids]
            data.update({'categories': categ_ids})

        woo_tag_ids = list(map(int, self.woo_tag_ids.mapped("woo_tag_id")))
        if all(woo_tag_ids):
            tag_ids = [{'id': tag_id} for tag_id in woo_tag_ids]
            data.update({'tags': tag_ids})
        return data

    def prepare_product_data(self, woo_template, publish, update_price, update_image, basic_detail):
        """
        This method is used to prepare a data for the export product.
        @param : elf, wcapi, instance, woo_template, publish, update_price, update_image, basic_detail, template,
        @return: data
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 15 September 2020 .
        Task_id: 165897
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        data = {}
        template = woo_template.product_tmpl_id
        instance = woo_template.woo_instance_id

        if basic_detail:
            name = woo_template.with_context(lang=instance.woo_lang_id.code).name or ""
            description = woo_template.with_context(lang=instance.woo_lang_id.code).woo_description or ""
            short_description = woo_template.with_context(lang=instance.woo_lang_id.code).woo_short_description or ""
            weight = self.convert_weight_by_uom(template.weight, instance)

            data = {
                'type': 'simple', 'name': name, 'description': description,
                'short_description': short_description, 'weight': str(weight),
                'taxable': woo_template.taxable and 'true' or 'false', 'shipping_required': 'true'
            }
            data = woo_template.add_woo_category_and_tags(data)

            attributes, is_variable = self.get_product_attribute(template, instance)
            if is_variable:
                data.update({'type': 'variable'})

            if template.attribute_line_ids:
                variations = []
                for variant in woo_template.woo_product_ids:
                    variation_data = {}
                    product_variant = self.get_variant_data(variant, instance, update_image)
                    variation_data.update(product_variant)
                    if update_price:
                        if data.get('type') == 'simple':
                            data.update(self.get_product_price(instance, variant))
                        else:
                            variation_data.update(self.get_product_price(instance, variant))
                    variations.append(variation_data)
                default_att = variations[0].get('attributes') if variations else []
                data.update({'attributes': attributes, 'default_attributes': default_att, 'variations': variations})
                if data.get('type') == 'simple':
                    data.update({'sku': str(variant.default_code),
                                 "manage_stock": variant.woo_is_manage_stock})
            else:
                variant = woo_template.woo_product_ids
                data.update(self.get_variant_data(variant, instance, update_image))
                if update_price:
                    data.update(self.get_product_price(instance, variant))

        data.update({'status': "publish" if publish == "publish" else "draft"})

        if update_image:
            tmpl_images = self.get_gallery_images(instance, woo_template, template)
            data.update({"images": tmpl_images})
        return data

    def convert_weight_by_uom(self, weight, instance, import_process=False):
        """
        This method converts weight from Odoo's weight uom to Woo's uom.
        @author: Maulik Barad on Date 24-Jun-2020.
        @param weight: Weight in float.
        @param instance: Instance of Woo.
        @param import_process: In which process, we are converting the weight import or export.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_weight_uom = instance.weight_uom_id
        product_weight_uom = self.env["product.template"]._get_weight_uom_id_from_ir_config_parameter()

        if woo_weight_uom != product_weight_uom:
            if import_process:
                weight = woo_weight_uom._compute_quantity(weight, product_weight_uom)
            else:
                weight = product_weight_uom._compute_quantity(weight, woo_weight_uom)
        return weight

    def export_woo_template(self, woo_template, data):
        """
        This method use to export woo template in Woo commerce store.
        @param : self
        @return: response
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 September 2020 .
        Task_id: 165897
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        instance = woo_template.woo_instance_id
        wc_api = instance.woo_connect()
        common_log_line_obj = self.env['common.log.lines.ept']
        template = woo_template.product_tmpl_id

        try:
            new_product = wc_api.post('products', data)
        except Exception as error:
            raise UserError(_("Something went wrong while Exporting Product.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        response = self.check_woocommerce_response(new_product, "Export Product", self._name, instance,
                                                   template)
        if not isinstance(response, dict):
            return False

        if response.get('data', {}) and response.get('data', {}).get('status') not in [200, 201]:
            message = response.get('message')
            if response.get('code') == 'woocommerce_rest_product_sku_already_exists':
                message = "%s, ==> %s" % (message, data.get('name'))
            common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=message, res_id=template.id)
            return False

        return response

    def export_woo_variants(self, variants, woo_tmpl_id, wcapi, woo_template):
        """
        This method use to export variations data in the Woocommerce store.
        @param : self, variants, woo_tmpl_id, wcapi
        @return: response_variations
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 September 2020 .
        Task_id: 165897
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        instance = woo_template.woo_instance_id
        common_log_line_obj = self.env['common.log.lines.ept']
        response_variations = []
        variant_batches = self.prepare_batches(variants)
        for woo_variants in variant_batches:
            try:
                variant_response = wcapi.post("products/%s/variations/batch" % woo_tmpl_id, {'create': woo_variants})
            except Exception as error:
                raise UserError(_("Something went wrong while Exporting Variants.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            if variant_response.status_code not in [200, 201]:
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, model_name=self._name,
                                                               message=variant_response.content,
                                                               res_id=woo_template.product_tmpl_id.id)
                continue
            try:
                response_variations += variant_response.json().get('create')
            except Exception as error:
                message = "Json Error : While retrieve product response from WooCommerce for instance %s. \n%s" % (
                    woo_template.woo_instance_id.name, error)
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, model_name=self._name,
                                                               message=message, res_id=woo_template.product_tmpl_id.id)
                continue

        return response_variations

    def woo_update_template_variant_data(self, response_variations, woo_template, response, woo_tmpl_id, publish):
        """
        This method uses to update the woo template and its variants which data receive from the WooCommerce store.
        @param : self
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 September 2020 .
        Task_id: 165897
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        template = woo_template.product_tmpl_id
        instance = woo_template.woo_instance_id
        for response_variation in response_variations:
            if response_variation.get('error'):
                common_log_line_obj.create_common_log_line_ept(operation_type="export", module="woocommerce_ept",
                                                               woo_instance_id=instance.id, model_name=self._name,
                                                               message=response_variation.get('error'),
                                                               res_id=woo_template.product_tmpl_id.id)
                continue
            self.update_woo_variant(response_variation, woo_template)

        created_at = response.get('date_created').replace('T', ' ')
        updated_at = response.get('date_modified').replace('T', ' ')

        if template.product_variant_count == 1 and not template.attribute_line_ids:
            woo_product = woo_template.woo_product_ids
            woo_product.write({'variant_id': woo_tmpl_id,
                               'created_at': created_at or False, 'updated_at': updated_at or False,
                               'exported_in_woo': True})
        total_variants_in_woo = len(response_variations) if response_variations else 1

        tmpl_data = {
            'woo_tmpl_id': woo_tmpl_id, 'created_at': created_at or False,
            'updated_at': updated_at or False, 'exported_in_woo': True,
            'total_variants_in_woo': total_variants_in_woo,
            "website_published": publish == 'publish'
        }
        woo_template.write(tmpl_data)
        return True

    def update_woo_variant(self, response_variation, woo_template):
        """
        This method updates variants after exported to WooCommerce.
        @param response_variation: Data returned from WooCommerce.
        @param woo_template: Record of the template of Woo layer.
        @author: Maulik Barad on Date 09-Nov-2020.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_obj = self.env['woo.product.product.ept']

        variant_sku = response_variation.get('sku')
        variant_id = response_variation.get('id')
        variant_created_at = response_variation.get('date_created').replace('T', ' ')
        variant_updated_at = response_variation.get('date_modified').replace('T', ' ')
        woo_product = woo_product_obj.search([('default_code', '=', variant_sku),
                                              ('woo_template_id', '=', woo_template.id),
                                              ('woo_instance_id', '=', woo_template.woo_instance_id.id)])
        response_variant_data = {
            'variant_id': variant_id, 'created_at': variant_created_at,
            'updated_at': variant_updated_at, 'exported_in_woo': True
        }
        woo_product and woo_product.write(response_variant_data)
        return True

    def get_product_link(self):
        """
        This method is used to redirect Woocommerce Product in WooCommerce Store.
        @author: Yagnik Joshi on Date 11-January-2023.
        @Task: 189557 - WC order link
        """
        self.ensure_one()
        product_link = "%s/wp-admin/post.php?post=%s&action=edit" % (self.woo_instance_id.woo_host, self.woo_tmpl_id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': product_link,
        }


class ProductProductEpt(models.Model):
    _name = "woo.product.product.ept"
    _order = 'product_id'
    _description = "WooCommerce Product"

    product_url = fields.Text("Product URL")
    name = fields.Char("Title")
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1)
    default_code = fields.Char()
    product_id = fields.Many2one("product.product", required=1, ondelete="cascade")
    woo_template_id = fields.Many2one("woo.product.template.ept", required=1, ondelete="cascade")
    active = fields.Boolean(default=True)
    exported_in_woo = fields.Boolean("Exported In WooCommerce")
    variant_id = fields.Char(size=120)
    fix_stock_type = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')])
    fix_stock_value = fields.Float(digits="Product UoS")
    created_at = fields.Datetime()
    updated_at = fields.Datetime()
    woo_is_manage_stock = fields.Boolean("Is Manage Stock?", default=True,
                                         help="Enable stock management at product level in WooCommerce")
    woo_image_ids = fields.One2many("woo.product.image.ept", "woo_variant_id")

    def toggle_active(self):
        """
        Archiving related woo product template if there is only one active woo product
        :parameter: self
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 09/12/2019.
        :Task id: 158502
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        with_one_active = self.filtered(lambda x: len(x.woo_template_id.woo_product_ids) == 1)
        for product in with_one_active:
            product.woo_template_id.toggle_active()
        return super(ProductProductEpt, self - with_one_active).toggle_active()

#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes product attributes, eBay product template
"""
import sys
import importlib
from datetime import datetime, timedelta
import logging
from odoo import models, fields, api
from odoo.tools.translate import html_translate
from odoo.tools.misc import split_every

importlib.reload(sys)
PYTHONIOENCODING = "UTF-8"
_EBAY_PRODUCT_LISTING_EPT = 'ebay.product.listing.ept'
_logger = logging.getLogger(__name__)


class EbayProductProductEpt(models.Model):
    """
    Describes eBay product details
    """
    _name = "ebay.product.product.ept"
    _description = "eBay Product Product"

    name = fields.Char(string='Product Name', size=256, required=True, help="Product Name")
    ebay_feedback_ids = fields.One2many(
        "ebay.feedback.ept", "ebay_product_id", string='ebay Feedback', help="eBay Feedback ids")
    instance_id = fields.Many2one('ebay.instance.ept', string='Instance', required=True, help="eBay Site")
    ebay_sku = fields.Char(string='Product Sku', size=64, help="eBay Product Sku")
    ebay_variant_id = fields.Char(string="Variant ID", help="eBay Variant Id")
    product_id = fields.Many2one("product.product", string="Product", ondelete="restrict", required=True,
                                 help="Odoo product id")
    ebay_product_tmpl_id = fields.Many2one(
        "ebay.product.template.ept", string="Product template", required=True,
        ondelete="cascade", help="eBay Product template Id")
    total_variant = fields.Integer(
        string="Total Variants", help="Gives total eBay product variants",
        related="ebay_product_tmpl_id.count_total_variants")
    exported_in_ebay = fields.Boolean(
        string="Exported Product To eBay", default=False,
        help="If product exported in eBay then returns True else False")
    ebay_stock_type = fields.Selection([
        ('fix', 'Fix'), ('percentage', 'Percentage')
    ], string='Fix Stock Type', help="eBay Stock Type")
    ebay_stock_value = fields.Float(string='Fix Stock Value', help="eBay Stock Value")
    code_type = fields.Selection([
        ('EAN', 'EAN'), ('ISBN', 'ISBN'), ('UPC', 'UPC')
    ], string='eBay ProductCode Type', default=False, help="eBay Product Code Type")
    ean13 = fields.Char(
        related="product_id.barcode", string="eBay Ean13", store=False, readonly=True, help="eBay Product Ean13")
    upc_number = fields.Char(string="UPC Number", help="eBay Product UPS Number")
    isbn_number = fields.Char(string="ISBN number", help="eBay Product ISBN Number")
    is_active_variant = fields.Boolean(
        string="Is Active eBay Product Variant", copy=False, default=False,
        help="If eBay Product Variant is active, returns True else False")
    ebay_active_listing_id = fields.Many2one(
        _EBAY_PRODUCT_LISTING_EPT, string="eBay Active Listing",
        compute="_compute_get_ebay_active_product", help="This field relocates eBay Product Listing")
    condition_enabled = fields.Boolean(
        string="eBay attribute Condition Enabled", default=False, compute="_compute_get_product_ebay_features",
        store=True, help="If eBay attribute condition enabled, then it returns True or False")
    condition_id = fields.Many2one('ebay.condition.ept', string='Condition', help="eBay conditions")
    condition_description = fields.Text(
        "Attribute Condition Description", help="Description for eBay attribute condition")
    category_id1 = fields.Many2one(
        'ebay.category.master.ept', related="ebay_product_tmpl_id.category_id1",
        string='Primary Category', help="Primary Category")
    category_id2 = fields.Many2one(
        'ebay.category.master.ept', related="ebay_product_tmpl_id.category_id2",
        string='Secondary Category', help="Secondary Category")
    attribute_id = fields.Many2one(
        "product.attribute", string="Variation Specific Image Attribute", compute="_compute_get_parent_attribute",
        store=True, help="This field relocates product attribute")
    description = fields.Html(
        string="Product Description", translate=html_translate, sanitize_attributes=False, help="Product Description")
    last_updated_qty = fields.Integer("Last Updated Qty Of Product", help="Last Updated Quantity of Product", default=0)

    def unlink(self):
        unlink_ebay_products = self.env['ebay.product.product.ept']
        unlink_ebay_templates = self.env['ebay.product.template.ept']
        for ebay_product in self:
            # Check if the product is last product of this template...
            other_products = self.search(
                [('ebay_product_tmpl_id', '=', ebay_product.ebay_product_tmpl_id.id), ('id', '!=', ebay_product.id)])
            if not other_products:
                unlink_ebay_templates |= ebay_product.ebay_product_tmpl_id
            unlink_ebay_products |= ebay_product
        res = super(EbayProductProductEpt, unlink_ebay_products).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        unlink_ebay_templates.unlink()
        self.clear_caches()
        return res

    def _compute_get_ebay_active_product(self):
        """
        Get active ebay product listings
        :return:
        """
        obj_ebay_product_listing_ept = self.env[_EBAY_PRODUCT_LISTING_EPT]
        for ebay_variant in self:
            ebay_prod_list = obj_ebay_product_listing_ept.search([
                ('ebay_variant_id', '=', ebay_variant.id),
                ('state', '=', 'Active')
            ], order='id desc', limit=1)
            ebay_variant.ebay_active_listing_id = ebay_prod_list.id if ebay_prod_list else False

    @api.depends("ebay_product_tmpl_id.attribute_id")
    def _compute_get_parent_attribute(self):
        """
        Get attribute of ebay product
        :return: product attribute
        """
        for record in self:
            record_attribute_id = record.ebay_product_tmpl_id.attribute_id
            record.attribute_id = record_attribute_id and record_attribute_id.id

    @api.depends('ebay_product_tmpl_id.category_id1', 'ebay_product_tmpl_id.category_id2')
    def _compute_get_product_ebay_features(self):
        """
        Calculates condition enabled or not for product categories
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        for record in self:
            if len(record.ebay_product_tmpl_id.ebay_variant_ids) == 1:
                record.condition_enabled = False
                category_id1 = record.ebay_product_tmpl_id.category_id1
                category_id2 = record.ebay_product_tmpl_id.category_id2
                if category_id1 or category_id2:
                    categ_id1_condition = (category_id1 and category_id1.condition_enabled)
                    categ_id2_condition = (category_id1 and category_id2.condition_enabled)
                    record.condition_enabled = categ_id1_condition or categ_id2_condition or False
            else:
                record.condition_enabled = False

    def update_price_in_ebay(self, instance, ebay_products=False):
        """
        Update ebay product price from odoo to ebay
        :param instance: current instance of ebay
        :param ebay_products:  ebay product object
        Migration done by Haresh Mori @ Emipro on date 1 January 2022 .
        """
        log_line_obj = self.env["common.log.lines.ept"]
        if not ebay_products:
            ebay_products = self.search([('instance_id', '=', instance.id), ('exported_in_ebay', '=', True)])
        if not ebay_products:
            message = "Products not found for update price. Instance(site) name: %s" % instance.name
            log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                    model_name='ebay.product.product.ept',
                                                    log_line_type='fail', mismatch=True, ebay_instance_id=instance.id)
            return False
        price_list_data = []
        for ebay_product in ebay_products:
            price = instance.pricelist_id._get_product_price(ebay_product.product_id, 1.0)
            ebay_variant_ids = ebay_product.ebay_product_tmpl_id.count_total_variants
            listing = self.get_active_ebay_product_listing(ebay_variant_ids, instance, ebay_product)
            if not listing:
                message = "No Active listing found for Update price in Site: %s and product:%s" % (
                    instance.name, ebay_product.ebay_sku)
                log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                        model_name='ebay.product.product.ept',
                                                        log_line_type='fail', mismatch=True,
                                                        ebay_instance_id=instance.id)
                continue
            sku = ebay_product.ebay_sku or ebay_product.product_id.default_code
            price_list_data = price_list_data + [{'ItemID': listing.name, 'StartPrice': price, 'SKU': sku}]

        self.export_price_stock_in_ebay(price_list_data, instance)

        return True

    def export_stock_levels_ebay(self, instance, ebay_products, ebay_product_stock=False):
        """
        Update product stock from odoo to ebay
        :param instance: current instance of ebay
        :param ebay_products:  ebay product object
        Migration done by Haresh Mori @ Emipro on date 3 January 2022 .
        """
        log_line_obj = self.env["common.log.lines.ept"]
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        out_of_stock = instance.allow_out_of_stock_product
        if self.env.context.get('is_call_from_operations_wizard', False):
            instance.write({'last_inventory_export_date': datetime.now()})
        inv_list_data = []
        for ebay_product in ebay_products:
            ebay_variant_ids = ebay_product.ebay_product_tmpl_id.count_total_variants
            listing = self.get_active_ebay_product_listing(ebay_variant_ids, instance, ebay_product)
            if not listing:
                message = "No Active listing found for Export Stock in Site: %s and product:%s" % (
                    instance.name, ebay_product.ebay_sku)
                log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                        model_name='ebay.product.product.ept',
                                                        log_line_type='fail', mismatch=True,
                                                        ebay_instance_id=instance.id)
                continue
            ebay_stock = ebay_product_stock[ebay_product.product_id.id]
            should_cancel_listing = ebay_product.ebay_product_tmpl_id._compute_get_listing_stock()
            if not out_of_stock and (should_cancel_listing or (int(ebay_stock) <= 0.0 and ebay_variant_ids == 1)):
                ebay_product_tmpl_obj.cancel_products_listing(listing, 'NotAvailable')
                continue
            inv_list_data = self.prepare_update_inventory_status_dict(ebay_product, ebay_variant_ids, listing,
                                                                      ebay_stock, ebay_product_stock, inv_list_data)

        self.export_price_stock_in_ebay(inv_list_data, instance)

        return True

    def prepare_update_inventory_status_dict(self, ebay_product, ebay_variant_ids, listing, ebay_stock,
                                             ebay_product_stock, inv_list):
        """
        Prepare dictionary to update inventory into eBay.
        :param ebay_product: eBay product object
        :param ebay_variant_ids: total variants of product
        :param listing: eBay product listing object
        :param ebay_stock: eBay product stock
        :param ebay_product_stock: all eBay product stock dictionary
        :param inv_list: dictionary of inventory status
        :return: dictionary of inventory status
        Migration done by Haresh Mori @ Emipro on date 3 January 2022 .
        """
        if int(ebay_stock) <= 0.0 and ebay_variant_ids > 1:
            ebay_product.write({'is_active_variant': False})
        total_stock = self.count_total_product_stock(ebay_product_stock, ebay_product)
        if total_stock != listing.ebay_stock:
            listing.ebay_stock = total_stock
        if ebay_stock != ebay_product.last_updated_qty:
            quantity = int(ebay_stock) if int(ebay_stock) >= 0 else 0
            ebay_product.last_updated_qty = quantity
            if ebay_variant_ids == 1:
                inv_list = inv_list + [{'ItemID': listing.name, 'Quantity': quantity}]
            else:
                inv_list = inv_list + [{'ItemID': listing.name, 'Quantity': quantity,
                                        'SKU': ebay_product.ebay_sku or ebay_product.product_id.default_code}]
        return inv_list

    def export_price_stock_in_ebay(self, list_data, instance):
        """
        This method is use to spilt data. Export stock and price in the eBay store
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 January 2022 .
        Task_id: 180143 - Update product Stock and Price
        """
        log_line_obj = self.env["common.log.lines.ept"]
        for inv_list in split_every(4, list_data):
            try:
                _logger.info("Data: %s" % str(inv_list))
                self.call_ebay_revise_inventory_status_api(list(inv_list), instance)
            except Exception as error:
                log_line_obj.create_common_log_line_ept(message=str(error), module='ebay_ept',
                                                        model_name='ebay.product.product.ept',
                                                        log_line_type='fail', mismatch=False,
                                                        ebay_instance_id=instance.id)

    def export_stock_in_ebay(self, instance):
        """
        This method is use export stock from the odoo to eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 January 2022 .
        Task_id: 180143 - Update product Stock and Price
        """
        ebay_product_template_obj = self.env["ebay.product.template.ept"]
        log_line_obj = self.env["common.log.lines.ept"]
        warehouse_ids = self.env['stock.warehouse'].browse(
            set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))

        if not warehouse_ids:
            message = "No Warehouse found for Export Stock in Site: %s" % instance.name
            log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                    model_name='ebay.product.product.ept',
                                                    log_line_type='fail', mismatch=True,
                                                    ebay_instance_id=instance.id)
            return False
        product_ids = self.get_products_to_export_stock(instance)
        if not product_ids:
            message = "No products found in warehouses: %s for Export Stock" % ', '.join(warehouse_ids.mapped('name'))
            log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                    model_name='ebay.product.product.ept',
                                                    log_line_type='fail', mismatch=True,
                                                    ebay_instance_id=instance.id)
            return False
        ebay_product_stock = ebay_product_template_obj.get_ebay_product_stock_ept(instance, product_ids,
                                                                                  warehouse_ids)
        ebay_exported_products = self.env["ebay.product.product.ept"].search([('product_id', 'in', product_ids),
                                                                              ('instance_id', '=', instance.id),
                                                                              ('exported_in_ebay', '=', True)])
        if not ebay_exported_products:
            message = "No Ebay products found in warehouses: %s for Export Stock and site: %s" % (
                ', '.join(warehouse_ids.mapped('name')), instance.name)
            log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                    model_name='ebay.product.product.ept',
                                                    log_line_type='fail', mismatch=True,
                                                    ebay_instance_id=instance.id)
            return False
        self.with_context(is_call_from_operations_wizard=True).export_stock_levels_ebay(instance,
                                                                                        ebay_exported_products,
                                                                                        ebay_product_stock)
        return True

    @staticmethod
    def create_query_for_get_free_quantities(location_ids, product_ids):
        """
        Prepare a query to get free quantities for active and ended product listings.
        :param location_ids: Stock warehouse ids
        :param product_ids: product ids
        :return: Query to get free quantities for active and ended product listings.
        """
        return """
        select T.listing_id,T.name,T.qty, T.ebay_sku from
        (select ebay_product_listing_ept.id as listing_id,ebay_product_listing_ept.name as name,
         ebay_product_product_ept.ebay_sku as ebay_sku,
        (select COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock from product_product pp
        left join stock_quant sq on pp.id = sq.product_id and sq.location_id in (%s)
        where pp.id in (ebay_product_product_ept.product_id) group by pp.id) as qty
        from ebay_product_listing_ept
        inner join ebay_product_product_ept on
        ebay_product_product_ept.ebay_product_tmpl_id=ebay_product_listing_ept.ebay_product_tmpl_id
        where state in ('Active','Ended') and ebay_product_product_ept.product_id in (%s)
        group by ebay_product_listing_ept.id,ebay_product_listing_ept.name, ebay_product_product_ept.product_id
        , ebay_product_product_ept.ebay_sku order by ebay_product_listing_ept.id)T
        """ % (str(",".join(map(str, location_ids))), str(",".join(map(str, product_ids))),)

    @staticmethod
    def create_query_for_get_forecasted_quantities(location_ids, product_ids):
        """
        Prepare a query to get forecasted quantities for active and ended product listings.
        :param location_ids: Stock warehouse ids
        :param product_ids: product ids
        :return: Query to get forecasted quantities for active and ended product listings.
        """
        return """
        select T.listing_id,T.name,T.qty, T.ebay_sku from
        (select ebay_product_listing_ept.id as listing_id,ebay_product_listing_ept.name as name,
        (select * from (select COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock from product_product pp
        left join stock_quant sq on pp.id = sq.product_id and sq.location_id in (%s)
        where pp.id in (ebay_product_product_ept.product_id) group by pp.id
        union all
        select sum(product_qty) as stock from stock_move where state in ('assigned')
        and product_id in (ebay_product_product_ept.product_id)
        and location_dest_id in (%s) group by product_id) as test) as forecasted_qty
        from ebay_product_listing_ept
        inner join ebay_product_product_ept on
        ebay_product_product_ept.ebay_product_tmpl_id=ebay_product_listing_ept.ebay_product_tmpl_id
        where state in ('Active','Ended') and ebay_product_product_ept.product_id in (%s)
        group by ebay_product_listing_ept.id,ebay_product_listing_ept.name, ebay_product_product_ept.product_id
        , ebay_product_product_ept.ebay_sku order by ebay_product_listing_ept.id)T
        """ % (str(",".join(map(str, location_ids))), str(",".join(map(str, location_ids))),
               str(",".join(map(str, product_ids))),)

    def get_active_ebay_product_listing(self, ebay_variant_ids, instance, ebay_product):
        """
        Search active product listing
        :param ebay_variant_ids: Total of eBay variant ids
        :param instance: eBay instance object
        :param ebay_product: eBay product object
        :return: eBay product listing object or False
        """
        listing = False
        if ebay_variant_ids == 1:
            listing = self.ebay_search_listing(instance, ebay_product.id, False)
        elif ebay_variant_ids > 1:
            listing = self.ebay_search_listing(instance, False, ebay_product.ebay_product_tmpl_id.id)
        return listing

    def update_inventory_status_via_api(self, inventory_list, total_ebay_export_products, instance, log_book_id):
        """
        Update product stock after every 4 product stock.
        :param inventory_list: Dictionary of export product stock.
        :param total_ebay_export_products: Total eBay products of which product stock is exported
        :param instance: eBay instance object
        :param log_book_id: common log book object
        :return: Dictionary of export product stock
        """
        common_log_lines_ept_obj = self.env['common.log.lines.ept']
        if len(inventory_list) == 4 or total_ebay_export_products == 0:
            try:
                self.call_ebay_revise_inventory_status_api(inventory_list, instance)
                inventory_list = []
            except Exception as error:
                find_common_message = common_log_lines_ept_obj.search(
                    [('message', '=ilike', error)])
                if not find_common_message:
                    log_book_id.write({'log_lines': [(0, 0, {'message': error})]})
        return inventory_list

    def get_products_to_export_stock(self, instance):
        """
        Get product ids that have stock movement is done after last export date.
        :param instance: eBay instance object
        :return: dictionary of product ids
        Migration done by Haresh Mori @ Emipro on date 3 January 2022 .
        # Deduct 5 hours from the below date for not skip any product in stock update time purpose.
        """
        instance_export_date = instance.last_inventory_export_date
        if not instance_export_date:
            instance_export_date = datetime.today() - timedelta(days=365)
        else:
            instance_export_date = instance_export_date - timedelta(hours=5)
        company_id = instance.warehouse_id.company_id
        product_ids = self.env['product.product'].get_products_based_on_movement_date_ept(instance_export_date,
                                                                                          company_id)
        return product_ids

    @staticmethod
    def count_total_product_stock(ebay_product_stock, ebay_product):
        """
        Count total stock of product.
        :param ebay_product_stock: Dictionary of product stock with product ids
        :param ebay_product: eBay product object
        :return: total of product stock
        Migration done by Haresh Mori @ Emipro on date 3 January 2022 .
        """
        total_stock = 0
        product_variants = ebay_product.product_id.product_tmpl_id.product_variant_ids
        for product_variant in product_variants:
            if product_variant.id in ebay_product_stock.keys():
                total_stock += ebay_product_stock[product_variant.id]
        return total_stock

    @staticmethod
    def call_ebay_revise_inventory_status_api(inventory_list, instance):
        """
        This Method relocate export inventory.
        :param inventory_list: Dictionary of inventory statuses which need to export.
        :param instance: eBay instance object.
        """
        inventory_export_dict = {'InventoryStatus': inventory_list}
        instance_language = instance.lang_id and instance.lang_id.code
        if instance_language:
            inventory_export_dict.update({'ErrorLanguage': instance_language})
        trading_api = instance.get_trading_api_object()
        trading_api.execute('ReviseInventoryStatus', inventory_export_dict)
        trading_api.response.dict()

    def ebay_search_listing(self, instance, ebay_variant_id, ebay_product_tmpl_id):
        """
        This Method relocate search eBay listing.
        :param instance: This Argument relocate eBay Instance.
        :param ebay_variant_id: This Argument relocate eBay variant id.
        :param ebay_product_tmpl_id: This Argument relocate eBay product template id.
        :return: This Method return eBay product listing.
        """
        ebay_product_listing_obj = self.env[_EBAY_PRODUCT_LISTING_EPT]
        listing_list = [
            ('name', '!=', False), ('instance_id', '=', instance.id),
            ('state', '=', 'Active'), ('is_cancel', '=', False)]
        if ebay_variant_id:
            listing_list.append(('ebay_variant_id', '=', ebay_variant_id))
        elif ebay_product_tmpl_id:
            listing_list.append(('ebay_product_tmpl_id', '=', ebay_product_tmpl_id))
        return ebay_product_listing_obj.search(listing_list, order='id desc', limit=1)

    def open_product_in_ebay(self):
        """
        This method is use to open the product in browser.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 18 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        self.ensure_one()
        product_url = ''
        if self.ebay_active_listing_id and self.ebay_active_listing_id.ebay_url:
            product_url = self.ebay_active_listing_id.ebay_url
        if product_url:
            return {'type': 'ir.actions.act_url', 'url': product_url, 'nodestroy': True, 'target': 'new'}
        return True

    def update_listing_time_and_state(self, instance, product_listing, log_book_id):
        """
        Update start time, end time and state into eBay listing
        :param instance: current instance of eBay
        :param product_listing: eBay product listing object.
        :param log_book_id: common log book ept object
        """
        common_log_lines_ept_obj = self.env['common.log.lines.ept']
        try:
            results = self.call_get_items_ebay_api(instance, product_listing.name)
            if results.get('Ack') == 'Success':
                start_time = results.get('Item', {}).get('ListingDetails', {}).get('StartTime')
                end_time = results.get('Item', {}).get('ListingDetails', {}).get('EndTime')
                product_listing.write({
                    'start_time': start_time.split(".", 1)[0].replace("T", " "),
                    'end_time': end_time.split(".", 1)[0].replace("T", " "),
                    'state': results.get('Item', {}).get('SellingStatus')['ListingStatus'],
                })
        except Exception as error:
            find_common_message = common_log_lines_ept_obj.search(
                [('message', '=ilike', error)])
            if not find_common_message:
                log_book_id.write({'log_lines': [(0, 0, {'message': error})]})

    def get_ebay_item_listing(self, instance, item_id):
        """
        Get item of ebay product from ebay API. Find SKU from existing product listing.
        If not found, then create eBay product listing.
        :param instance: current instance of ebay
        :param item_id: item id received from ebay API
        :return: sku of item or blank
        """
        res = ''
        product_listing_obj = self.env[_EBAY_PRODUCT_LISTING_EPT]
        results = {}
        try:
            results = self.call_get_items_ebay_api(instance, item_id)
        except Exception as error:
            _logger.info(error)
            return res
        if results.get('Ack') == 'Success':
            item = results.get('Item')
            listing_record = product_listing_obj.search_product_listing_by_name(item.get('ItemID'), instance.id)
            if listing_record and listing_record[0].ebay_variant_id and listing_record[0].ebay_variant_id.ebay_sku:
                return listing_record[0].ebay_variant_id.ebay_sku or False
            self.search_or_create_ebay_product_and_template_with_listing(item, instance)
            res = item.get('SKU')
        return res

    def search_or_create_ebay_product_and_template_with_listing(self, item, instance):
        """
        Search or create eBay product, product template and create eBay product listing.
        :param item: items received from eBay.
        :param instance: eBay instance object
        """
        product_listing_obj = self.env[_EBAY_PRODUCT_LISTING_EPT]
        ebay_product_template_obj = self.env['ebay.product.template.ept']
        if item.get('SKU', False):
            listing_type = item.get('ListingType')
            ebay_product = product_listing_obj.search_ebay_product_by_sku(item.get('SKU'), instance.id)
            odoo_product = product_listing_obj.search_odoo_product_by_sku(item.get('SKU'))
            if ebay_product:
                ebay_product_template_obj.create_ebay_product_listing(
                    False, instance, item, ebay_product.ebay_product_tmpl_id, listing_type, ebay_product.id)
            elif odoo_product:
                ebay_product_tmpl_id = product_listing_obj.search_or_create_ebay_product_template(
                    odoo_product.product_tmpl_id.id, instance.id, item.get('Title'), item.get('Description'))
                product_variant_ids = odoo_product.product_tmpl_id.product_variant_ids.ids
                # commented below code because of product_id and instance_id fields not in product.product model it
                # is giving issue at import unshipped ordet time so for resolve that commented it.
                # commented below 2 line code by Harsh Parekh on 20/04/2021.
                # variants = odoo_product.product_tmpl_id.product_variant_ids.filtered(
                #     lambda x: x.product_id not in product_variant_ids and x.instance_id == instance.id)
                for variant in product_variant_ids:
                    ebay_product = self.create_ebay_product(instance.id, variant, ebay_product_tmpl_id.id)
                    if variant.default_code == item.get('SKU', False):
                        ebay_product.write({'exported_in_ebay': True})
                        ebay_product_template_obj.create_ebay_product_listing(
                            False, instance, item, ebay_product.ebay_product_tmpl_id,
                            listing_type, ebay_product.id)

    @staticmethod
    def call_get_items_ebay_api(instance, item_id):
        """
        Call GETItems eBay API.
        :param instance: eBay instance object
        :param item_id: eBay item id.
        :return: response received from api.
        """
        trading_api = instance.get_trading_api_object()
        trading_api.execute('GetItem', {'ItemID': item_id})
        return trading_api.response.dict()

    def create_ebay_product(self, instance_id, variant, ebay_product_tmpl_id):
        """
        Create eBay product.
        :param instance_id: eBay instance id
        :param variant: product product object
        :param ebay_product_tmpl_id: eBay product template id
        :return: eBay product product object
        """
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        ebay_prod_values = {
            'ebay_sku': variant.default_code, 'product_id': variant.id, 'instance_id': instance_id,
            'ebay_product_tmpl_id': ebay_product_tmpl_id, 'name': variant.product_tmpl_id.name}
        return ebay_product_product_obj.create(ebay_prod_values)

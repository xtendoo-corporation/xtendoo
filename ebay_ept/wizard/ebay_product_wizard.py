#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes operations for eBay products.
"""
from odoo import models, fields

EBAY_PRODUCT_TEMPLATE = 'ebay.product.template.ept'
EBAY_PRODUCT_EPT = 'ebay.product.product.ept'


class EbayProductWizard(models.TransientModel):
    """
    Describes ebay products related operations
    """
    _name = 'ebay.product.wizard'
    _description = "eBay Product Wizard"
    template_id = fields.Many2one(
        'ebay.template.ept', string="Select Listing Template",
        help="Selected Template Configuration will be applied to the Listing Products")
    publish_in_ebay = fields.Boolean('Start Listing Immediately', help="Will Active Product Immediately on eBay")
    schedule_time = fields.Datetime(
        string='Scheduled Time', help="Time At which the product will be active on eBay")
    ending_reason = fields.Selection([
        ('Incorrect', 'The start price or reserve price is incorrect'),
        ('LostOrBroken', 'The item was lost or broken'),
        ('NotAvailable', 'The item is no longer available for sale'),
        ('OtherListingError', 'The listing contained an error'),
        ('SellToHighBidder', 'The listing has qualifying bids')
    ], string='Ending Product Listing Reason', help=' Reason of ending product listing.')

    def update_payment_in_ebay(self):
        """
        Updates payment in ebay if any account move is found.
        """
        active_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].search([('id', 'in', active_ids)])
        for invoice in invoices:
            invoice.update_payment_in_ebay()
        return True

    def product_template_update_stock_in_ebay(self):
        """
        This method is use to update the product stock from Odoo to eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 January 2022 .
        Task_id: 180143 - Update product Stock and Price
        """
        log_line_obj = self.env["common.log.lines.ept"]
        ebay_product_template_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        ebay_product_ept = self.env[EBAY_PRODUCT_EPT]
        active_ids = self._context.get('active_ids', [])
        ebay_product_template = ebay_product_template_obj.browse(active_ids).filtered(lambda l: l.instance_id.active)
        ebay_instances = ebay_product_template.mapped('instance_id')
        ebay_product_template_variant = ebay_product_template.mapped('ebay_variant_ids').ids
        ebay_products = ebay_product_ept.browse(ebay_product_template_variant)
        for instance in ebay_instances:
            ebay_exported_products = self.search_ebay_products_by_instance_id(instance.id, ebay_products)
            warehouse_ids = self.env['stock.warehouse'].browse(
                set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))
            if not warehouse_ids:
                message = "No Warehouse found for Export Stock in Site: %s" % instance.name
                log_line_obj.create_common_log_line_ept(message=message,
                                                        module='ebay_ept', ebay_instance_id=instance.id,
                                                        model_name='ebay.product.product.ept',
                                                        log_line_type='fail', mismatch=True)
                continue
            odoo_products = ebay_products.mapped('product_id')
            ebay_product_stock = ebay_product_template_obj.get_ebay_product_stock_ept(instance, odoo_products.ids,
                                                                                      warehouse_ids)
            if ebay_exported_products:
                ebay_products.export_stock_levels_ebay(instance, ebay_exported_products, ebay_product_stock)
        return True

    def update_product_template_price_in_ebay(self):
        """
        This method is use to update the product price from Odoo to Ebay Store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 1 January 2022 .
        Task_id: 180924 - Export Products / Variants
        """
        ebay_product_template_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        ebay_product_ept = self.env[EBAY_PRODUCT_EPT]
        active_ids = self._context.get('active_ids', [])
        ebay_product_templates = ebay_product_template_obj.browse(active_ids).filtered(lambda l:
                                                                                       l.instance_id.active
                                                                                       and l.exported_in_ebay)
        ebay_instances = ebay_product_templates.mapped('instance_id')
        ebay_template_variants = ebay_product_templates.mapped('ebay_variant_ids').ids
        ebay_product_product = ebay_product_ept.browse(ebay_template_variants)
        for instance in ebay_instances:
            ebay_products = self.search_ebay_products_by_instance_id(instance.id, ebay_product_product)
            if ebay_products:
                ebay_products.update_price_in_ebay(instance, ebay_products)

    @staticmethod
    def search_ebay_products_by_instance_id(instance_id, ebay_product_product):
        """
        Search eBay products which are already exported.
        :param instance_id: eBay instance id
        :param ebay_product_product: eBay product object
        :return: eBay product object
        """
        return ebay_product_product.filtered(lambda l: l.instance_id.id == instance_id and l.exported_in_ebay)

    def export_product_in_ebay(self):
        """
        This method is use to export product from Odoo to eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 24 December 2021.
        Task_id: 180924 - Export Products / Variants
        """
        self.ensure_one()
        ebay_product_tmpl_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        active_ids = self._context.get('active_ids', [])
        ebay_product_template = ebay_product_tmpl_obj.browse(active_ids).filtered(lambda x: not x.exported_in_ebay)
        if ebay_product_template:
            if ebay_product_template.count_total_variants == 1:
                ebay_product_tmpl_obj.export_individual_item(ebay_product_template, self.publish_in_ebay,
                                                             self.schedule_time)
            else:
                ebay_product_tmpl_obj.export_variation_item(ebay_product_template, self.publish_in_ebay,
                                                            self.schedule_time)
        return True

    def update_product_in_ebay(self):
        """
        This method is use to update the existing product values in the eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 30 December 2021 .
        Task_id: 180924 - Export Products / Variants
        """
        self.ensure_one()
        ebay_product_tmpl_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        active_ids = self._context.get('active_ids', [])
        ebay_product_template = ebay_product_tmpl_obj.browse(active_ids).filtered(lambda x: x.exported_in_ebay)
        if ebay_product_template:
            if ebay_product_template.count_total_variants == 1:
                ebay_product_tmpl_obj.update_individual_item(ebay_product_template, self.publish_in_ebay,
                                                             self.schedule_time)
            else:
                ebay_product_tmpl_obj.update_variation_item(ebay_product_template, self.publish_in_ebay,
                                                            self.schedule_time)
        return True

    def relist_product_in_ebay(self):
        """
        This method is use to Relist products from Odoo to eBay
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 December 2021 .
        Task_id: 180924 - Export Products / Variants
        """
        self.ensure_one()
        ebay_product_tmpl_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        active_ids = self._context.get('active_ids', [])
        ebay_product_template = ebay_product_tmpl_obj.browse(active_ids).filtered(lambda x: x.exported_in_ebay)
        product_listing = ebay_product_template.product_listing_ids.filtered(
            lambda x:
            x.ebay_product_tmpl_id == ebay_product_template and x.instance_id == ebay_product_template.instance_id
            and x.state == 'Ended')
        if ebay_product_template and product_listing:
            product_listing = product_listing.sorted(reverse=True)[0]
            ebay_product_tmpl_obj.relist_products(ebay_product_template, ebay_product_template.instance_id,
                                                  product_listing)
        return True

    @staticmethod
    def search_ended_product_listings(ebay_product_template, ebay_variant):
        """
        Search product listings which are ended.
        :param ebay_product_template: eBay product template object
        :param ebay_variant: eBay product object
        :return: eBay product listing object
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        return ebay_product_template.product_listing_ids.filtered(
            lambda x: x.state == 'Ended' and x.ebay_variant_id == ebay_variant)

    def cancel_product_listing_in_ebay(self):
        """
        This method is use to cancel the product listing in eBay store.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 December 2021 .
        Task_id: 180924 - Export Products / Variants
        """
        self.ensure_one()
        ebay_product_tmpl_obj = self.env[EBAY_PRODUCT_TEMPLATE]
        active_ids = self._context.get('active_ids', [])
        ebay_product_template = ebay_product_tmpl_obj.browse(active_ids).filtered(
            lambda x: x.exported_in_ebay and x.ebay_active_listing_id)
        if ebay_product_template:
            if ebay_product_template.count_total_variants == 1:
                ebay_product_tmpl_obj.cancel_products_listing(
                    ebay_product_template.ebay_variant_ids.ebay_active_listing_id, self.ending_reason)
            else:
                ebay_product_tmpl_obj.cancel_products_listing(ebay_product_template.ebay_active_listing_id,
                                                              self.ending_reason)
        return True

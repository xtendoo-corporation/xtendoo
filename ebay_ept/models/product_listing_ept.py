#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay product listings
"""
import json
import time
import logging
from time import gmtime
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_EBAY_PRODUCT_TEMPLATE_EPT = 'ebay.product.template.ept'
_EBAY_PRODUCT_PRODUCT_EPT = 'ebay.product.product.ept'
_EBAY_SITE_DETAILS = 'ebay.site.details'
_PRODUCT_ATTRIBUTE = 'product.attribute'
_PRODUCT_PRODUCT = 'product.product'


class EbayProductListingEpt(models.Model):
    """
    Describes eBay Product Listing fields and methods.
    """
    _name = "ebay.product.listing.ept"
    _description = "eBay Product Listing"

    name = fields.Char(string='Item ID', size=64, required=True, help='Product Name')
    ebay_feedback_ids = fields.One2many(
        "ebay.feedback.ept", "listing_id", string='FeedBack', help='Feedbacks from eBay')
    ebay_product_tmpl_id = fields.Many2one(
        _EBAY_PRODUCT_TEMPLATE_EPT, string='Product Name', ondelete="cascade", readonly=True,
        help='eBay Product Template')
    ebay_variant_id = fields.Many2one(
        _EBAY_PRODUCT_PRODUCT_EPT, string='Variant Name', readonly=True, help='Record of Product Variant')
    instance_id = fields.Many2one('ebay.instance.ept', string='Site Name', help='eBay Instance')
    end_time = fields.Datetime(string='Product Listing End Time', help='End Date & Time of Product Listing')
    start_time = fields.Datetime(
        string='Product Listing Start Time', help='Start Date & Time of Product Listing')
    is_cancel = fields.Boolean(
        string='Is Cancelled Product Listing?', readonly=True, help='Is Cancelled Product Listing?')
    cancel_listing = fields.Boolean(string='Cancel Product Listing', help='Cancel Product Listing')
    ending_reason = fields.Selection([
        ('Incorrect', 'The start price or reserve price is incorrect'),
        ('NotAvailable', 'The item is no longer available for sale'),
        ('LostOrBroken', 'The item was lost or broken'),
        ('OtherListingError', 'The listing contained an error'),
        ('SellToHighBidder', 'The listing has qualifying bids')
    ], string='Product Ending Reason', help='Reason for ending product from listing')
    ebay_template_id = fields.Many2one('ebay.template.ept', string='Listing Template', help='Record for eBay template')
    time_remain_function = fields.Char(
        compute="_compute_get_time_remain", string='Remaining Time',
        help='Calculates Remaining time for product in a listing')
    state = fields.Selection([
        ('Active', 'Active'), ('Completed', 'Completed'), ('Custom', 'Custom'),
        ('CustomCode', 'CustomCode'), ('Ended', 'Ended')
    ], string='Status', default="Active", help='Describes eBay Product listing status')
    listing_type = fields.Selection([('FixedPriceItem', 'Fixed Price')], string='Product Listing Type',
                                    default='FixedPriceItem', required=True, help="Describes product listing type")
    listing_duration = fields.Selection([
        ('Days_3', '3 Days'), ('Days_5', '5 Days'), ('Days_7', '7 Days'), ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'), ('GTC', 'Good \'Til Cancelled (only for fixed price)')
    ], string='Product Listing Duration', default='Days_7', help='Product Listing Duration')
    ebay_stock = fields.Integer(string="Remaining Stock", help="Remaining stock of the active eBay product")
    ebay_total_sold_qty = fields.Integer(string="Total Sold Qty", help="Total sold quantity in eBay")
    ebay_url = fields.Char(string="Product URL", help="Active eBay product URL.")
    ebay_site_id = fields.Many2one(_EBAY_SITE_DETAILS, string='eBay Site', help='Record of eBay site')

    @api.depends('end_time')
    def _compute_get_time_remain(self):
        """
        Calculates remaining time of product listing
        :return: remaining time of product listing
        """
        locate = ''
        locate_first = False
        listing_date_time_format = "%Y-%m-%d %H:%M:%S"
        for cur_record in self:
            if cur_record.state != 'Ended':
                cur_rec_end_time = cur_record.end_time
                gmt_tm = time.strftime(listing_date_time_format, gmtime())
                new_gmt_time = datetime.strptime(gmt_tm, listing_date_time_format)
                trunc_time = str(new_gmt_time)[:19]
                if cur_rec_end_time:
                    time_remaining = ''
                    time_remain1 = cur_rec_end_time - datetime.strptime(trunc_time, listing_date_time_format)
                    time_remain = time_remain1 + (datetime.utcnow() - datetime.now())
                    time_split = str(time_remain).split('.')
                    if time_split:
                        time_remaining = time_split[0]
                    locate = time_remaining
                    locate_first = locate[0]
                if locate_first == '-':
                    cur_record.state = 'Ended'
                    self._cr.execute("UPDATE ebay_product_listing_ept SET state='Ended' where id=%d" % cur_record.id)
                    self._cr.commit()
            cur_record.time_remain_function = locate

    def prepare_values_for_product_listing(self, instance, item, ebay_product):
        """
        This method is use to prepare vas for product listing.
        @return: vals of product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        ebay_site_ids = self.search_ebay_site_by_name(item.get('Site'))
        list_details = item.get('ListingDetails')
        vals = {
            'name': item.get('ItemID'),
            'instance_id': instance.id,
            'start_time': list_details.get('StartTime').split(".", 1)[0].replace("T", " "),
            'end_time': list_details.get('EndTime').split(".", 1)[0].replace("T", " "),
            'listing_duration': item.get('ListingDuration'),
            'ebay_product_tmpl_id': ebay_product.ebay_product_tmpl_id.id,
            'ebay_variant_id': ebay_product.id,
            'ebay_total_sold_qty': item.get('SellingStatus')['QuantitySold'],
            'ebay_stock': item.get('Quantity'),
            'ebay_url': item.get('ListingDetails')['ViewItemURL'],
            'ebay_site_id': ebay_site_ids and ebay_site_ids.id or False,
            'state': item.get('SellingStatus')['ListingStatus']
        }
        return vals

    def update_active_listing_categories(self, item, prod_listing_id):
        """
        This method is use to update the categories in the active listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        ebay_product_template = prod_listing_id.ebay_product_tmpl_id
        primary_category = self.search_or_create_primary_category_for_product_listing(ebay_product_template, item)
        secondary_category = self.search_or_create_secondary_category_for_product_listing(ebay_product_template, item)
        ebay_store_cat1 = self.get_store_category_for_product_listing(item.get('Storefront', {}).get('StoreCategoryID'),
                                                                      ebay_product_template.store_categ_id1)
        ebay_store_cat2 = self.get_store_category_for_product_listing(
            item.get('Storefront', {}).get('StoreCategory2ID'), ebay_product_template.store_categ_id2)
        ebay_product_template.write({
            'category_id1': primary_category and primary_category.id,
            'category_id2': secondary_category and secondary_category.id,
            'store_categ_id1': ebay_store_cat1 and ebay_store_cat1.id,
            'store_categ_id2': ebay_store_cat2 and ebay_store_cat2.id
        })
        _logger.info(
            "Category and Store category is updated in the eBay product template: %s" % ebay_product_template.name)
        return True

    def search_or_create_primary_category_for_product_listing(self, product_template, item):
        """
        This method is use to Create or get primary category for a product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        primary_category = False
        ebay_category_master_obj = self.env['ebay.category.master.ept']
        primary_category_id = item.get('PrimaryCategory', {}).get('CategoryID')
        category_name = item.get('PrimaryCategory').get('CategoryName')
        if primary_category_id:
            primary_category = product_template.category_id1.filtered(
                lambda x: x.ebay_category_id == primary_category_id)
            if not primary_category:
                primary_category = ebay_category_master_obj.search(
                    [('ebay_category_id', '=', primary_category_id), ('site_id', '=', product_template.site_id.id)],
                    limit=1)
            if not primary_category:
                primary_category = ebay_category_master_obj.create(
                    {'name': category_name, 'ebay_category_id': primary_category_id,
                     'site_id': product_template.site_id.id})
        return primary_category

    def search_or_create_secondary_category_for_product_listing(self, product_template, item):
        """
        This method is use to Create or get secondary category for a product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        secondary_category = False
        ebay_category_master_obj = self.env['ebay.category.master.ept']
        secondary_category_id = item.get('SecondaryCategory', {}).get('CategoryID')
        if secondary_category_id:
            secondary_category = product_template.category_id2.filtered(
                lambda x: x.ebay_category_id == secondary_category_id)
            if not secondary_category:
                secondary_category = ebay_category_master_obj.search(
                    [('ebay_category_id', '=', secondary_category_id), ('site_id', '=',
                                                                        product_template.site_id.id)], limit=1)
            if not secondary_category:
                secondary_category = ebay_category_master_obj.create(
                    {'name': item.get('SecondaryCategory').get('CategoryName'),
                     'ebay_category_id': secondary_category_id, 'site_id': product_template.site_id.id
                     })
        return secondary_category

    @staticmethod
    def get_store_category_for_product_listing(store_cat, store_cat_id):
        """
        Return eBay store category.
        :param store_cat: Store category reurn from eBay.
        :param store_cat_id: eBay category master ept object
        :return: eBay category master ept object or False
        """
        ebay_store_cat = False
        if store_cat:
            ebay_store_cat = store_cat_id.filtered(lambda x: x.ebay_category_id == store_cat and x.is_store_category)
        return ebay_store_cat

    def create_update_seller_policy(self, product_response, prod_listing_id):
        """
        This method is use to create/update seller policy and set those policy in ebay product template.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        policy_vals = {}
        site_policy_obj = self.env['ebay.site.policy.ept']
        ebay_product_template = prod_listing_id.ebay_product_tmpl_id
        _logger.info("=Processing to set policy for ebay template: %s" % ebay_product_template.name)
        instance_id = ebay_product_template.instance_id
        seller_profiles = product_response.get('SellerProfiles', {})
        if not seller_profiles:
            return False
        seller_shipping_profile = seller_profiles.get('SellerShippingProfile', {})
        seller_return_profile = seller_profiles.get('SellerReturnProfile', {})
        seller_payment_profile = seller_profiles.get('SellerPaymentProfile', {})
        if seller_shipping_profile.get('ShippingProfileID', ''):
            shipping_policy = site_policy_obj.search([('policy_id', '=',
                                                       seller_shipping_profile.get('ShippingProfileID')),
                                                      ('policy_type', '=', 'SHIPPING'),
                                                      ('instance_id', '=', instance_id.id)], limit=1)
            if not shipping_policy:
                shipping_policy = site_policy_obj.create(
                    {'name': seller_shipping_profile.get('ShippingProfileName'),
                     'policy_id': seller_shipping_profile.get('ShippingProfileID'), 'policy_type': 'SHIPPING',
                     'instance_id': instance_id.id})
            _logger.info("=Shipping policy : %s" % shipping_policy.name)
            policy_vals.update({'ebay_seller_shipping_policy_id': shipping_policy.id})
        if seller_return_profile.get('ReturnProfileID', ''):
            return_policy = site_policy_obj.search([('policy_id', '=',
                                                     seller_return_profile.get('ReturnProfileID')),
                                                    ('policy_type', '=', 'RETURN_POLICY'),
                                                    ('instance_id', '=', instance_id.id)], limit=1)
            if not return_policy:
                return_policy = site_policy_obj.create(
                    {'name': seller_return_profile.get('ReturnProfileName'),
                     'policy_id': seller_return_profile.get('ReturnProfileID'), 'policy_type': 'RETURN_POLICY',
                     'instance_id': instance_id.id})
            _logger.info("=Return policy : %s" % return_policy.name)
            policy_vals.update({'ebay_seller_return_policy_id': return_policy.id})
        if seller_payment_profile.get('PaymentProfileID', ''):
            payment_policy = site_policy_obj.search([('policy_id', '=',
                                                      seller_payment_profile.get('PaymentProfileID')),
                                                     ('policy_type', '=', 'PAYMENT'),
                                                     ('instance_id', '=', instance_id.id)], limit=1)
            if not payment_policy:
                payment_policy = site_policy_obj.create(
                    {'name': seller_payment_profile.get('PaymentProfileName'),
                     'policy_id': seller_payment_profile.get('PaymentProfileID'), 'policy_type': 'PAYMENT',
                     'instance_id': instance_id.id})
            policy_vals.update({'ebay_seller_payment_policy_id': payment_policy.id})
            _logger.info("=Seller policy : %s" % payment_policy.name)
        if policy_vals:
            ebay_product_template.write(policy_vals)

        return True

    def create_variant_ebay_product_images(self, sku, ebay_pics, ebay_product):
        """
        This method is use to create images of eBay products.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        product_attribute = self.env[_PRODUCT_ATTRIBUTE].search(
            [('name', '=ilike', ebay_pics.get('VariationSpecificName'))], limit=1)
        ebay_variation_specific_picture_set = ebay_pics.get('VariationSpecificPictureSet')
        if not isinstance(ebay_variation_specific_picture_set, list):
            ebay_variation_specific_picture_set = [ebay_variation_specific_picture_set]
        for ebay_var_spec_pic_set in ebay_variation_specific_picture_set:
            product_attr_value = product_attribute.value_ids.filtered(
                lambda x: x.name == ebay_var_spec_pic_set.get('VariationSpecificValue'))
            odo_product_id = ebay_product.product_id.filtered(
                lambda x:
                x.default_code == sku and
                product_attr_value in x.product_template_attribute_value_ids.product_attribute_value_id)
            if odo_product_id:
                ebay_picture_urls = ebay_var_spec_pic_set.get('PictureURL')
                if not isinstance(ebay_picture_urls, list):
                    ebay_picture_urls = [ebay_picture_urls]
                self.create_or_update_product_images(ebay_picture_urls, ebay_product)

    def create_individual_ebay_product_images(self, product_response, ebay_product):
        """
        Create images for product without variants
        :param product_response: item response from ebay
        :param ebay_product: ebay product object
        :return:
        """
        picture_details = product_response.get('PictureDetails')
        picture_urls = picture_details.get('PictureURL')
        if picture_details and picture_urls:
            if not isinstance(picture_urls, list):
                picture_urls = [picture_urls]
            self.create_or_update_product_images(picture_urls, ebay_product)

    def create_or_update_product_images(self, picture_urls, ebay_product):
        """
        If product image not found, then create new product image other wise update it.
        :param picture_urls: Pictures received from eBay API
        :param ebay_product: eBay Product Product objecte
        """
        common_product_image_ept_obj = self.env['common.product.image.ept']
        ebay_product_id = False
        ebay_product_template_id = False
        instance_id = False
        if ebay_product:
            ebay_product_id = ebay_product.id
            ebay_product_template_id = ebay_product.ebay_product_tmpl_id.id
            instance_id = ebay_product.instance_id.id
        for picture_url in picture_urls:
            ebay_prod_image = ''
            prod_image = common_product_image_ept_obj.get_image_ept(picture_url)
            common_prod_image = ebay_product.product_id.ept_image_ids.filtered(lambda x: x.image == prod_image)
            ebay_product_image_values = self.prepare_ebay_product_image_values(ebay_product, picture_url, prod_image)
            if not ebay_prod_image:
                ebay_image_ids = self.update_ebay_product_image_values(
                    ebay_product_id, ebay_product_template_id, picture_url, prod_image, instance_id)
                if not common_prod_image:
                    ebay_product_image_values.update(ebay_image_ids)
                    common_product_image_ept_obj.create(ebay_product_image_values)
                else:
                    common_prod_image.write(ebay_image_ids)
            elif not ebay_prod_image.odoo_image_id:
                if not common_prod_image:
                    common_prod_image = common_product_image_ept_obj.create(ebay_product_image_values)
                ebay_prod_image.write({'odoo_image_id': common_prod_image.id})

    @staticmethod
    def prepare_ebay_product_image_values(ebay_product, picture_url, prod_image):
        """
        Prepare dictionary for common product image values.
        :param ebay_product: eBay product product object
        :param picture_url: eBay image url
        :param prod_image: binary eBay product image
        :return: Dictionary for common product image values
        """
        return {
            'product_id': ebay_product.product_id.id,
            'template_id': ebay_product.ebay_product_tmpl_id.product_tmpl_id.id,
            'url': picture_url or '',
            'image': prod_image
        }

    @staticmethod
    def update_ebay_product_image_values(ebay_product_id, ebay_product_template_id, picture_url, prod_image,
                                         instance_id):
        """
        Prepare dictionary eBay Image Ids.
        :param ebay_product_id: eBay product id
        :param ebay_product_template_id: eBay product template id
        :param picture_url: Image URL.
        :param prod_image: Binary product image
        :param instance_id: eBay instance id
        :return: Dictionary for eBay image ids.
        """
        return {
            'ebay_image_ids': [(0, 0, {
                'ebay_variant_id': ebay_product_id,
                'ebay_product_template_id': ebay_product_template_id,
                'url': picture_url or '',
                'image': prod_image,
                'instance_id': instance_id,
            })]
        }

    @staticmethod
    def get_item_listing(instance, item_id):
        """
        Get Item listing from ebay API
        :param instance: current instance of ebay
        :param item_id: item id received from response of ebay
        :return: item listing
        """
        item = {}
        try:
            api_obj = instance.get_trading_api_object()
            product_dict = {'ItemID': item_id, 'DetailLevel': 'ItemReturnDescription'}
            api_obj.execute('GetItem', product_dict)
            results = api_obj.response.dict()
            if results.get('Ack') == 'Success':
                item = results.get('Item')
        except Exception as error:
            raise UserError(_('%s', (str(error))))
        return item if item else {}

    def set_variant_sku(self, variations, product_template):
        """
        Set SKU for product variants
        :param variations: product variants
        :param product_template: ebay product template object
        :return: True
        """
        odoo_product_obj = self.env[_PRODUCT_PRODUCT]
        for variation in variations:
            sku = variation.get('SKU')
            variation_specifics = variation.get('VariationSpecifics')
            name_value_list = variation_specifics.get('NameValueList')
            domain = []
            odoo_product = False
            if not isinstance(name_value_list, list):
                name_value_list = [name_value_list]
            attribute_value_ids = self.prepare_ebay_product_template_attribute_values(
                name_value_list, product_template.id)
            for attribute_value_id in attribute_value_ids:
                domain.append(('product_template_attribute_value_ids', '=', attribute_value_id))
            if domain:
                domain.append(('product_tmpl_id', '=', product_template.id))
                odoo_product = odoo_product_obj.search(domain)
            if odoo_product:
                odoo_product.write({'default_code': sku})
        return True

    def prepare_ebay_product_template_attribute_values(self, name_value_list, product_template_id):
        """
        Prepare dictionary product template attribute line values.
        :param name_value_list: attribute list received from eBay.
        :param product_template_id: odoo product template object
        :return: Dictionary of product template attribute values
        """
        product_attribute_obj = self.env[_PRODUCT_ATTRIBUTE]
        product_attribute_value_obj = self.env['product.attribute.value']
        attribute_value_ids = []
        for name_value in name_value_list:
            attrib_values = name_value.get('Value')
            product_attribute = product_attribute_obj.get_attribute(name_value.get('Name'))
            if product_attribute:
                product_attr_value = product_attribute_value_obj.get_attribute_values(
                    attrib_values, product_attribute.id)
                if product_attr_value:
                    template_attribute_value_id = self.env['product.template.attribute.value'].search([
                        ('product_attribute_value_id', '=', product_attr_value.id),
                        ('attribute_id', '=', product_attribute.id),
                        ('product_tmpl_id', '=', product_template_id)], limit=1)
                    if template_attribute_value_id:
                        attribute_value_ids.append(template_attribute_value_id.id)
        return attribute_value_ids

    def create_variant_products(self, item, variations, instance, sku, listing, is_sync_stock, is_sync_price,
                                product_template):
        """
        Creates variant products, eBay product, eBay template and sync product stock and price.
        :param item: Item received from eBay.
        :param variations: Variations of eBay product.
        :param instance: eBay instance object
        :param sku: eBay product sku
        :param listing: eBay product listing object or False.
        :param is_sync_stock: If True, product stock will be sync.
        :param is_sync_price: If True, product price will be sync.
        :param product_template: product template object or False
        :return: eBay product listing object or False.
        """
        product_template_obj = self.env['product.template']
        prod_template_title = item.get('Title') if item.get('Title') else ''
        # product_description = item.get('Description') if item.get('Description') else ''
        start_price = item.get('StartPrice').get('value') or 0.0
        attrib_line_values = self.prepare_ebay_attribute_values(variations)
        if attrib_line_values and not product_template:
            product_template = product_template_obj.create({
                'name': prod_template_title,
                'list_price': start_price,
                'type': 'product',
                # 'description_sale': product_description,
                "attribute_line_ids": attrib_line_values,
                "invoice_policy": "order"
            })
        self.set_variant_sku(variations, product_template)
        self.sync_product_stock_price(item, is_sync_stock, is_sync_price, instance, sku)
        ebay_product_tmpl_id = self.search_or_create_ebay_product_template(
            product_template.id, instance.id, item.get('Title'), item.get('Description'))
        listing = self.search_or_create_ebay_product(
            instance, item, product_template.product_variant_ids, sku,
            ebay_product_tmpl_id.id, listing)
        self.create_update_seller_policy(item, listing)
        return listing, product_template

    def check_any_variation_is_exist_with_sku(self, variations, product_template):
        """
        Check whether Odoo product template is exist or not.
        :param variations: eBay product variations
        :param product_template: True or False
        :return: True or False
        """
        for variation in variations:
            odoo_product = self.search_odoo_product_by_sku(variation.get('SKU'))
            if odoo_product:
                product_template = True
                break
        return product_template

    def prepare_ebay_attribute_values(self, variations):
        """
        Prepare product attribute value dictionary.
        :param variations: Variations of eBay product.
        :return: Dictionary of product attribute values.
        """
        product_attribute_obj = self.env[_PRODUCT_ATTRIBUTE]
        attrib_line_values = []
        attribute_value_ids = {}
        for variation in variations:
            variation_specifics = variation.get('VariationSpecifics')
            name_value_list = variation_specifics.get('NameValueList')
            if not isinstance(name_value_list, list):
                name_value_list = [name_value_list]
            for name_value in name_value_list:
                attrib_name = name_value.get('Name')
                attribute = product_attribute_obj.get_attribute(attrib_name, auto_create=True)
                attr_val_ids = self.prepare_product_attribute_value_dict(name_value, attribute.id)
                if attr_val_ids:
                    attribute_value_ids = self.update_ebay_attribute_values_dict(
                        attribute_value_ids, attribute, attr_val_ids)
        for attribute_id in attribute_value_ids:
            attribute_line_ids_data = (0, 0, {
                'attribute_id': attribute_id, 'value_ids': attribute_value_ids[attribute_id]})
            attrib_line_values.append(attribute_line_ids_data)
        return attrib_line_values

    def prepare_product_attribute_value_dict(self, name_value, attribute_id):
        """
        Prepare dictionary for eBay attribute values.
        :param name_value: attribute values list
        :param attribute_id: eBay attribute id
        :return: dictionary for eBay attribute values
        """
        product_attribute_value_obj = self.env['product.attribute.value']
        attr_val = name_value.get('Value')
        attrib_values = [attr_val] if not isinstance(attr_val, list) else attr_val
        attr_val_ids = []
        for attrib_value in attrib_values:
            attribute_value = product_attribute_value_obj.get_attribute_values(
                attrib_value, attribute_id, auto_create=True)
            attr_val_ids.append(attribute_value.id)
        return attr_val_ids

    @staticmethod
    def update_ebay_attribute_values_dict(attribute_value_ids, attribute, attr_val_ids):
        """
        Update eBay attribute_value_ids dictionary.
        :param attribute_value_ids: dictionary of attribute_val_ids
        :param attribute: eBay attribute
        :param attr_val_ids: dictionary attribute values
        :return: attribute_value_ids dictionary
        """
        if attribute_value_ids:
            if attribute_value_ids and attribute.id in attribute_value_ids.keys():
                if attr_val_ids[0] not in attribute_value_ids[attribute.id]:
                    attribute_value_ids[attribute.id].append(attr_val_ids[0])
            else:
                attribute_value_ids.update({attribute.id: attr_val_ids})
        else:
            attribute_value_ids.update({attribute.id: attr_val_ids})
        return attribute_value_ids

    def search_ebay_site_by_name(self, ebay_site):
        """
        Search eBay site details from given eBay site.
        :param ebay_site: eBay site name
        :return: eBay site details object
        """
        ebay_site_details_obj = self.env[_EBAY_SITE_DETAILS]
        return ebay_site_details_obj.search([('name', '=', ebay_site)], limit=1)

    def search_ebay_product_by_sku(self, sku, instance_id):
        """
        Search eBay product by sku.
        :param sku: eBay product sku
        :param instance_id: eBay instance id.
        :return: eBay product product object
        """
        ebay_product_product_obj = self.env[_EBAY_PRODUCT_PRODUCT_EPT]
        return ebay_product_product_obj.search([('ebay_sku', '=', sku), ('instance_id', '=', instance_id)], limit=1)

    def search_ebay_product_by_product_id(self, variant_id, instance_id):
        """
        Search eBay product by product id.
        :param variant_id: product id
        :param instance_id: eBay instance id
        :return: eBay product product object
        """
        ebay_product_product_obj = self.env[_EBAY_PRODUCT_PRODUCT_EPT]
        return ebay_product_product_obj.search([('product_id', '=', variant_id), ('instance_id', '=', instance_id)],
                                               limit=1)

    def search_odoo_product_by_sku(self, sku):
        """
        Search Odoo product by sku.
        :param sku: product sku
        :return: product product object
        """
        product_product_obj = self.env[_PRODUCT_PRODUCT]
        return product_product_obj.search([('default_code', '=', sku)],limit=1)

    def search_ebay_product_template(self, odoo_product_tmpl_id, instance_id):
        """
        Search eBay product template.
        :param odoo_product_tmpl_id: Odoo product template id
        :param instance_id: eBay instance id
        :return: eBay product template object
        """
        ebay_product_template_obj = self.env[_EBAY_PRODUCT_TEMPLATE_EPT]
        return ebay_product_template_obj.search(
            [('product_tmpl_id', '=', odoo_product_tmpl_id), ('instance_id', '=', instance_id)])

    def search_product_listing_by_name(self, listing_name, instance_id):
        """
        This method is use to search product listing by name.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        return self.search([('name', '=', listing_name), ('instance_id', '=', instance_id)], limit=1)

    def search_or_create_ebay_product_template(self, odoo_product_tmpl_id, instance_id, item_title, item_description):
        """
        This method is use to create or search the eBay template.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        ebay_product_template_obj = self.env[_EBAY_PRODUCT_TEMPLATE_EPT]
        ebay_product_tmpl_id = self.search_ebay_product_template(odoo_product_tmpl_id, instance_id)
        if not ebay_product_tmpl_id:
            prod_tmpl_vals = {'name': item_title, 'instance_id': instance_id, 'exported_in_ebay': True,
                              'description': item_description, 'product_tmpl_id': odoo_product_tmpl_id
                              }
            ebay_product_tmpl_id = ebay_product_template_obj.create(prod_tmpl_vals)
        return ebay_product_tmpl_id

    def create_ebay_product_listing(self, instance, item, ebay_product):
        """
        This method is use to create a ebay product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        value = self.prepare_values_for_product_listing(instance, item, ebay_product)
        return self.create(value)

    def map_odoo_product_with_ebay_product(self, ebay_product, item, is_create_auto_odoo_product):
        """
        Check if odoo product is not mapped with eBay product then check odoo product is exist or not.
        If odoo product is exist then mapped with ebay product.
        If Odoo product is not exist and auto create product is True,
        then create Odoo product and mapped with eBay Product.
        :param ebay_product: eBay product product object
        :param item: item received from eBay.
        :param is_create_auto_odoo_product: If checked, it will allow to create Odoo product if not found.
        """
        if not ebay_product.product_id:
            odoo_product = self.search_odoo_product_by_sku(item.get('SKU'))
            if not odoo_product and is_create_auto_odoo_product:
                odoo_product = self.create_odoo_product(item.get('Title'), item.get('SKU'))
            if odoo_product:
                ebay_product.write({'product_id': odoo_product.id})

    def search_or_create_ebay_product(self, instance, item, odoo_product_variant_ids, sku, ebay_product_tmpl_id,
                                      listing=False):
        """
        This method is use to create a eBay product.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        for variant in odoo_product_variant_ids:
            ebay_product_variant = self.search_ebay_product_by_product_id(variant.id, instance.id)
            if not ebay_product_variant and variant.default_code == sku:
                ebay_product_id = self.create_ebay_product(
                    variant, ebay_product_tmpl_id, instance.id, item.get('Description'))
                if not listing:
                    listing = self.create_ebay_product_listing(instance, item, ebay_product_id)
                    self.update_active_listing_categories(item, listing)
                    self.create_update_seller_policy(item, listing)
                try:
                    if item.get('PictureDetails'):
                        self.create_individual_ebay_product_images(item, ebay_product_id)
                except Exception as error:
                    _logger.info("Receiving error while updating images in variant product %s" % error)
        return listing

    def create_ebay_product(self, variant, ebay_product_tmpl_id, instance_id, description):
        """
        This method is use to create new ebay product.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        value = {
            'product_id': variant.id,
            'ebay_sku': variant.default_code,
            'ebay_product_tmpl_id': ebay_product_tmpl_id,
            'instance_id': instance_id,
            'name': variant.product_tmpl_id.name,
            'description': description,
            'exported_in_ebay': True
        }
        return ebay_product_product_obj.create(value)

    def sync_variation_product_listings(self, instance, item, variations, product_queue_line):
        """
        This method is use to sync the variation products of product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        log_line_obj = self.env['common.log.lines.ept']
        listing = False
        product_template = False
        item_id = item.get('ItemID')
        item_dict = self.get_item_listing(instance, item_id)
        _logger.info("Start the variation process of itemid: %s" % item_id)
        for variation in variations:
            sku = variation.get('SKU')
            if not sku:
                continue
            _logger.info("Variation Processing SKU: %s of itemid: %s" % (sku, item_id))
            ebay_product = self.search_ebay_product_by_sku(sku, instance.id)
            if ebay_product:
                self.update_existing_ebay_product(instance, item, ebay_product, item_dict, sku)
                continue
            odoo_product = self.search_odoo_product_by_sku(sku)
            if odoo_product and len(odoo_product) > 1:
                message = 'More than one Odoo Product found with SKU %s' % sku
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='ebay.product.listing.ept',
                                                                   log_line_type='fail', mismatch=True,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'import_product_queue_line_id': product_queue_line.id})
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': True})
                continue
            product_template = self.check_any_variation_is_exist_with_sku(variations, product_template)
            if odoo_product:
                self.sync_product_stock_price(item, product_queue_line.is_sync_stock, product_queue_line.is_sync_price,
                                              instance, sku)
                ebay_product_tmpl_id = self.search_or_create_ebay_product_template(odoo_product.product_tmpl_id.id,
                                                                                   instance.id, item.get('Title'),
                                                                                   item.get('Description'))
                listing = self.search_or_create_ebay_product(instance, item,
                                                             odoo_product.product_tmpl_id.product_variant_ids, sku,
                                                             ebay_product_tmpl_id.id, listing)
                self.create_update_seller_policy(item, listing)
                self.update_active_listing_categories(item, listing)
            elif not odoo_product and not product_template and product_queue_line.is_create_auto_odoo_product:
                try:
                    listing, product_template = self.create_variant_products(item, variations, instance, sku, listing,
                                                                             product_queue_line.is_sync_stock,
                                                                             product_queue_line.is_sync_price,
                                                                             product_template)
                except Exception as error:
                    message = "Getting error while creating product, error is: %s" % error
                    _logger.info(message)
                    log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                       model_name='ebay.product.listing.ept',
                                                                       log_line_type='fail', mismatch=False,
                                                                       ebay_instance_id=instance.id)
                    log_line.write({'import_product_queue_line_id': product_queue_line.id})
                    self.env.context = dict(self.env.context)
                    self.env.context.update({'is_product_queue_fail': True})
                    continue
            else:
                message = 'Product Not found for SKU %s' % sku
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='ebay.product.listing.ept',
                                                                   log_line_type='fail', mismatch=True,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'import_product_queue_line_id': product_queue_line.id})
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': True})
        _logger.info("End the variation process of itemid: %s" % item_id)
        return True

    def update_existing_ebay_product(self, instance, item, ebay_product, item_dict, sku):
        """
        Create active listing and product images for existing eBay product.
        :param instance: eBay instance object.
        :param item: item received from eBay.
        :param ebay_product: eBay product object
        :param item_dict: dictionary of item by item id.
        :param sku: eBay sku
        """
        try:
            listing = self.create_ebay_product_listing(instance, item, ebay_product)
            _logger.info("New listing created: %s" % listing.name)
            if listing:
                self.update_active_listing_categories(item, listing)
            ebay_pics = item_dict.get('Variations', {}) and item_dict.get('Variations', {}).get('Pictures', {})
            if ebay_pics:
                _logger.info("Update Images of ebay product: %s and SKU: %s" % (ebay_product.name, sku))
                self.create_variant_ebay_product_images(sku, ebay_pics, ebay_product)
        except Exception as error:
            _logger.info("Getting error while update existing product:%s" % error)

    def sync_product_listings(self, queue_line):
        """
        This method is use to Sync product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        log_line_obj = self.env['common.log.lines.ept']
        product_response = json.loads(queue_line.product_data)
        site_name = product_response.get('Site', '')
        instance = self.env['ebay.instance.ept'].search([('site_id.name', '=', site_name),('seller_id', '=', queue_line.seller_id.id)])
        if not instance:
            message = "Cannot be able to find eBay instance for site %s!" % site_name
            log_line = log_line_obj.create_common_log_line_ept(message=message, model_name='ebay.product.listing.ept',
                                                               log_line_type='fail', mismatch=True, module='ebay_ept',
                                                               ebay_instance_id=instance.id)
            log_line.write({'import_product_queue_line_id': queue_line.id})
            self.env.context = dict(self.env.context)
            self.env.context.update({'is_product_queue_fail': True})
            return False
        product_listing = self.search_product_listing_by_name(product_response['ItemID'], instance.id)
        _logger.info("Start Processing ItemId: %s and name: %s" % ((product_response['ItemID']), product_response.get(
            'Title')))
        if product_listing:
            self.update_product_listing(product_response, product_listing)
        else:
            self.create_or_update_product_with_listings(instance, product_response, queue_line)
        _logger.info("End Processing ItemId: %s and name: %s" % ((product_response['ItemID']), product_response.get(
            'Title')))
        return True

    def create_or_update_product_with_listings(self, instance, product_response, queue_line):
        """
        This method us use to create/update the product with listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        log_line_obj = self.env['common.log.lines.ept']
        variations = product_response.get('Variations', {}).get('Variation')
        if variations:
            if not isinstance(variations, list):
                variations = [variations]
            self.sync_variation_product_listings(instance, product_response, variations, queue_line)
        elif product_response.get('SKU', False):
            self.create_or_update_product(product_response, instance, queue_line)
        else:
            message = "Product Have no SKU for itemid: %s" % product_response.get('ItemID')
            log_line = log_line_obj.create_common_log_line_ept(message=message, model_name='ebay.product.listing.ept',
                                                               log_line_type='fail', mismatch=True, module='ebay_ept',
                                                               ebay_instance_id=instance.id)
            log_line.write({'import_product_queue_line_id': queue_line.id})
            self.env.context = dict(self.env.context)
            self.env.context.update({'is_product_queue_fail': True})
        return True

    def update_product_listing(self, product_response, product_list):
        """
        This method is used to update the existing product listing.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        ebay_product = product_list.ebay_product_tmpl_id.ebay_variant_ids[0]
        if product_response.get('SKU', False):
            try:
                if product_response.get('PictureDetails'):
                    self.create_individual_ebay_product_images(product_response, ebay_product)
            except Exception as error:
                _logger.info("Receiving Error %s" % error)

        self.update_active_listing(product_response, product_list)

    def update_active_listing(self, product_response, product_list):
        """
        Update existing product listing values.
        :param product_response: product response received from eBay.
        :param product_list: eBay product list object.
        """
        ebay_site_ids = self.search_ebay_site_by_name(product_response.get('Site'))
        listing_start_time = product_response.get('ListingDetails')['StartTime']
        listing_end_time = product_response.get('ListingDetails')['EndTime']
        values = {
            'start_time': listing_start_time.split(".", 1)[0].replace("T", " "),
            'end_time': listing_end_time.split(".", 1)[0].replace("T", " "),
            'ebay_total_sold_qty': product_response.get('SellingStatus')['QuantitySold'],
            'state': product_response.get('SellingStatus')['ListingStatus'],
            'ebay_stock': product_response.get('Quantity'),
            'ebay_url': product_response.get('ListingDetails')['ViewItemURL'],
            'listing_duration': product_response.get('ListingDuration'),
            'ebay_site_id': ebay_site_ids and ebay_site_ids.id or False
        }
        product_list.write(values)
        self.update_active_listing_categories(product_response, product_list)
        self.create_update_seller_policy(product_response, product_list)

    def create_or_update_product(self, item, instance, product_queue_line):
        """
        Create or Update eBay And Odoo Product
        :param item: Item received from eBay
        :param instance: Instance of eBay
        :param is_create_auto_odoo_product: If True, it will create odoo product other wise not
        :param is_sync_stock: If True, Product stock will be synced from Odoo to eBay
        :param is_sync_price: If True, Product price will be synced from Odoo to eBay
        :param product_queue_line: eBay import product queue
        :param error: If any error, returns True
        :param ebay_pr_sku: Dictionary of eBay Products
        :return: error (True/ False)
        """
        log_line_obj = self.env['common.log.lines.ept']
        is_create_auto_odoo_product = product_queue_line.is_create_auto_odoo_product
        is_sync_price = product_queue_line.is_sync_price
        is_sync_stock = product_queue_line.is_sync_stock
        ebay_sku = item.get('SKU')
        ebay_product = self.search_ebay_product_by_sku(ebay_sku, instance.id)
        if ebay_product:
            try:
                if item.get('PictureDetails'):
                    self.create_individual_ebay_product_images(item, ebay_product)
            except Exception as error:
                message = "Getting Error while create image %s " % error
                _logger.info(message)
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='ebay.product.listing.ept',
                                                                   log_line_type='fail', mismatch=False,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'import_product_queue_line_id': product_queue_line.id})
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': True})
            self.map_odoo_product_with_ebay_product(ebay_product, item, is_create_auto_odoo_product)
            product_listing_id = self.create_ebay_product_listing(instance, item, ebay_product)
            self.sync_product_stock_price(item, product_queue_line.is_sync_stock, is_sync_price, instance, ebay_sku)
            self.update_active_listing_categories(item, product_listing_id)
            self.create_update_seller_policy(item, product_listing_id)
        else:
            odoo_product = self.search_odoo_product_by_sku(ebay_sku)
            if not odoo_product and is_create_auto_odoo_product:
                odoo_product = self.create_odoo_product(item.get('Title'), item.get('SKU'))
            if odoo_product and len(odoo_product) > 1:
                message = 'More than one Odoo Product found with SKU %s' % item.get('SKU')
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='ebay.product.listing.ept',
                                                                   log_line_type='fail', mismatch=True,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'import_product_queue_line_id': product_queue_line.id})
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': True})
                return False
            if odoo_product and len(odoo_product) == 1:
                self.sync_product_stock_price(item, is_sync_stock, is_sync_price, instance, ebay_sku)
                ebay_product_tmpl_id = self.search_or_create_ebay_product_template(
                    odoo_product.product_tmpl_id.id, instance.id, item.get('Title'), item.get('Description'))
                self.search_or_create_ebay_product(
                    instance, item, odoo_product.product_tmpl_id.product_variant_ids, ebay_sku,
                    ebay_product_tmpl_id.id)
            else:
                message = 'Product Not found for SKU %s' % (item.get('SKU'))
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='ebay.product.listing.ept',
                                                                   log_line_type='fail', mismatch=True,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'import_product_queue_line_id': product_queue_line.id})
                self.env.context = dict(self.env.context)
                self.env.context.update({'is_product_queue_fail': True})
            return True

    def create_odoo_product(self, title, sku):
        """
        Creates Odoo product.
        :param title: Product Name.
        :param sku: Product sku.
        :return: product product object.
        """
        product_product_obj = self.env[_PRODUCT_PRODUCT]
        odoo_product_values = {
            'name': title, 'default_code': sku, 'type': 'product'}
        return product_product_obj.create(odoo_product_values)

    def sync_product_stock_price(self, item, is_sync_stock, is_sync_price, instance, ebay_sku):
        """
        This method is use to sync product stock and price.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        stock_quant = self.env['stock.quant']
        product_product_obj = self.env[_PRODUCT_PRODUCT]
        odoo_product = product_product_obj.search([('default_code', '=', ebay_sku), ('detailed_type', '=', 'product')],
                                                  limit=1)
        if odoo_product:
            if is_sync_stock and instance.warehouse_id:
                stock_inventory_array = {odoo_product.id: float(item.get('Quantity'))}
                name = 'eBay' + '_' + instance.name + '_' + odoo_product.name
                warehouse = instance.warehouse_id
                stock_quant.create_inventory_adjustment_ept(stock_inventory_array, warehouse.lot_stock_id, True, name)
                _logger.info(
                    "Update product quantity:%s for product sku: %s" % (float(item.get('Quantity')), odoo_product.name))
            if is_sync_price:
                price = float(item.get('StartPrice').get('value'))
                _logger.info("Update product price:%s for product sku: %s" % (price, odoo_product.name))
                instance.pricelist_id.set_product_price_ept(odoo_product.id, price)

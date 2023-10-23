#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes product attributes, eBay product template
"""
import sys
import time
import importlib
import html
import cgi
from datetime import datetime
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)
importlib.reload(sys)
_IMPORT_CATEGORY_MASTER_EPT = 'ebay.category.master.ept'
_EBAY_PRODUCT_LISTING = 'ebay.product.listing.ept'
_NOT_APPLIED = 'Does not Apply'
EBAY_SITE_POLICY = 'ebay.site.policy.ept'
ShippingPackageAttributes = [
    'PackageDepth', 'PackageLength', 'PackageWidth', 'WeightMajor',
    'WeightMinor', 'ShippingIrregular', 'ShippingPackage'
]


class EbayProductTemplateEpt(models.Model):
    """
    Defines Template of exported eBay Product.
    """
    _name = "ebay.product.template.ept"
    _description = "eBay Product Template"

    should_cancel_listing = fields.Boolean(
        string="Should Cancel Listing From eBay", compute="_compute_get_listing_stock")
    name = fields.Char(string='Product Name', size=256, required=True, help="Product Name")
    instance_id = fields.Many2one('ebay.instance.ept', string='Instance', required=True, help="eBay Instance")
    title = fields.Char(string="Title Of Product Template", help="Title Of Product Template")
    bold_title = fields.Boolean(
        string='Bold Title Of Product Template?', default=False, help='Bold Title Of Product Template?')
    exported_in_ebay = fields.Boolean(
        string="Exported Product To eBay?", default=False, help="True if Exported Product To eBay")
    description = fields.Html(string="Product Description", translate=True, sanitize=False, help="Product Description")
    ebay_stock_type = fields.Selection([
        ('fix', 'Fix'), ('percentage', 'Percentage')], string='Fix Stock Type', help="eBay fix product stock type")
    ebay_stock_value = fields.Float(string='Fix Stock Value', help="eBay product stock fix value")
    product_tmpl_id = fields.Many2one(
        "product.template", string="Odoo Product Template", ondelete='restrict',
        required=True, help="Odoo Product Template")
    ebay_variant_ids = fields.One2many(
        "ebay.product.product.ept", "ebay_product_tmpl_id", string="Variants", help="eBay Product Variants")
    attribute_id = fields.Many2one(
        "product.attribute", string="Variation Specific Image Attribute", help="Variation Specific Image Attribute")
    ebay_fee_ids = fields.One2many("ebay.fee.ept", "ebay_product_tmpl_id", string="eBay Fees", help="eBay Fees")
    product_listing_ids = fields.One2many(
        "ebay.product.listing.ept", "ebay_product_tmpl_id", string="Product Listing", help="eBay Product listing")
    condition_id = fields.Many2one('ebay.condition.ept', string='Condition', help="eBay Product template condition")
    condition_description = fields.Text(
        string="Description of Attribute Condition", help="Description of Attribute Condition")
    category_id1 = fields.Many2one(_IMPORT_CATEGORY_MASTER_EPT, string='Primary Category', help="Primary Category")
    category_id2 = fields.Many2one(_IMPORT_CATEGORY_MASTER_EPT, string='Secondary Category', help="Secondary Category")
    store_categ_id1 = fields.Many2one(_IMPORT_CATEGORY_MASTER_EPT, string='Store CategoryID', help="Store Category")
    store_categ_id2 = fields.Many2one(_IMPORT_CATEGORY_MASTER_EPT, string='Store Category2ID', help="Store Category")
    attribute_ids = fields.One2many(
        'ebay.attribute.matching', 'product_tmpl_id', string='Attribute Values', help='eBay Attribute Values')
    ebay_active_listing_id = fields.Many2one(
        _EBAY_PRODUCT_LISTING, string="eBay Active Listing",
        compute="_compute_get_ebay_active_product", search="_search_ebay_active_product", help="eBay active listing")
    condition_enabled = fields.Boolean(
        string="Attribute Condition Enabled", default=False, compute="_compute_get_ebay_features",
        store=True, help="If True, Attribute has Condition")
    auto_pay_enabled = fields.Boolean(
        string="Auto Pay Enable", default=False, compute="_compute_get_ebay_features",
        store=True, help="If True, Auto Pay is Enabled")
    set_return_policy = fields.Boolean(
        string="Return Policy", default=False, compute="_compute_get_ebay_features",
        store=True, help="If True, product template has return policy")
    digital_good_delivery_enabled = fields.Boolean(
        string="Digital Good Delivery Enabled?", default=False, compute="_compute_get_ebay_features",
        store=True, help="Digital Good Delivery Enabled")
    site_id = fields.Many2one(
        "ebay.site.details", string="eBay Site", readonly=True,
        compute="_compute_get_site_id", store=True, help="eBay Site")
    is_immediate_payment = fields.Boolean(
        string="Immediate Payment", default=False, help="If True, Immediate Payment is enabled")
    digital_delivery = fields.Boolean(
        string="Digital Delivery Of Product", default=False, help="If True, digital delivery of product is available")
    uuid_type = fields.Char(string="UUIDType", size=32, help="universally unique identifier for an item")
    count_total_variants = fields.Integer(
        string="Total Variants", compute="_compute_get_count_variants", help="Total Variants")
    count_exported_variants = fields.Integer(
        string="Exported Variants", compute="_compute_get_count_variants", help="Total exported variants")
    count_active_variants = fields.Integer(
        string="Active Variants", compute="_compute_get_count_variants", help="Total active variants")
    related_dynamic_desc = fields.Boolean(
        string="Related Dynamic Description?", related="instance_id.seller_id.use_dynamic_desc")
    desc_template_id = fields.Many2one(
        "ebay.description.template", string="Description Templates", help="Set Custom Description Template")
    ebay_listing_duration = fields.Selection([
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'),
        ('GTC', 'Good \'Til Cancelled (only for fixed price)')], string='Duration', default='GTC')
    # eBay Seller Policy
    ebay_seller_payment_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Payment Policy", help="Options for Seller Payment Policy")
    ebay_seller_return_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="eBay Seller Return Policy", help="Options for Seller Return Policy")
    ebay_seller_shipping_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Shipping Policy", help="Options for Seller Shipping Policy")
    listing_type = fields.Selection([('FixedPriceItem', 'Fixed Price')], string='Listing Type',
                                    default='FixedPriceItem')
    ebay_template_id = fields.Many2one('mail.template', string='Description Template',
                                       ondelete='set null', help='This field contains the template that will be used.')
    hand_time = fields.Selection([
        ('0', 'Same Business Day'), ('1', '1 Business Day'), ('2', '2 Business Days'), ('3', '3 Business Days'),
        ('4', '4 Business Days'), ('5', '5 Business Days'), ('10', '10 Business Days'), ('15', '15 Business Days'),
        ('20', '20 Business Days'), ('30', '30 Business Days')
    ], string='Handling Tme', required=True, default="1", help="Business days in which order will be delivered")
    product_attribute_ids = fields.Many2many(
        "product.attribute", string="Variation Specific Image Attributes", help="Variation Specific Image Attributes")
    common_log_book_id = fields.Many2one('common.log.book.ept', compute='_compute_log_book_of_ebay_template')
    common_log_line_ids = fields.One2many(comodel_name="common.log.lines.ept", inverse_name="ebay_product_tmpl_id",
                                          string="Common Log Lines")

    def _compute_log_book_of_ebay_template(self):
        for record in self:
            record.common_log_book_id = False
            log_book_id = self.env['common.log.book.ept'].search(
                [('res_id', '=', record.id), ('ebay_instance_id', '=', record.instance_id.id)], limit=1)
            if log_book_id:
                record.write({'common_log_book_id': log_book_id.id})

    def view_log_lines(self):
        """
        This method is use to redirect in log book view from the template product screen.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 19 January 2022 .
        """
        log_lines = self.common_log_line_ids
        action = self.env['ir.actions.actions']._for_xml_id("ebay_ept.action_ebay_process_job_log_lines_ept")
        views = [(self.env.ref("ebay_ept.ebay_process_job_log_line_tree_view_ept").id, 'tree'),
                 (self.env.ref("ebay_ept.ebay_process_job_log_line_form_view_ept").id, 'form')]
        if len(log_lines) == 1:
            views.pop(0)
            action['res_id'] = log_lines.ids[0]
        elif len(log_lines) <= 0:
            raise UserError("There are no Log Lines generated yet for selected eBay Product Template!")
        action['views'] = views
        action['domain'] = [('id', 'in', log_lines.ids)]
        action['context'] = {}
        return action

    @api.depends('instance_id', 'instance_id.site_id')
    def _compute_get_site_id(self):
        for record in self:
            record.site_id = record.instance_id.site_id

    def _compute_get_listing_stock(self):
        if len(self.ebay_variant_ids.ids) > 1:
            count = 0
            for variant in self.ebay_variant_ids:
                warehouse_ids = self.env['stock.warehouse'].browse(
                    set(variant.instance_id.ebay_stock_warehouse_ids.ids + variant.instance_id.warehouse_id.ids))
                stock = self.get_ebay_product_stock_ept(variant.instance_id, [variant.product_id.id],
                                                        warehouse_ids)
                if stock[variant.product_id.id] <= 0.0:
                    count = count + 1
            if count == len(self.ebay_variant_ids.ids):
                self.should_cancel_listing = True
        else:
            self.should_cancel_listing = False

    def _compute_get_count_variants(self):
        """
        Calculates total, exported and active variants
        :return: Get total, exported and active variants
        """
        for record in self:
            total_exported = 0
            total_active = 0
            record.count_total_variants = len(record.ebay_variant_ids)
            if record.count_total_variants > 1:
                self.set_active_and_exported_variants_for_variant_product(record, total_active)
            else:
                for variant in record.ebay_variant_ids:
                    ebay_active_listing_id = variant.ebay_active_listing_id
                    if variant.exported_in_ebay:
                        total_exported += 1
                    if ebay_active_listing_id and ebay_active_listing_id.state == 'Active':
                        total_active += 1
                record.count_exported_variants = total_exported
                record.count_active_variants = total_active

    @staticmethod
    def set_active_and_exported_variants_for_variant_product(record, total_active):
        """
        Set active and exported variants for variation type product.
        :param record: eBay product template record
        :param total_active: Total active incremental variable
        """
        if record.exported_in_ebay and record.ebay_active_listing_id:
            record.count_exported_variants = len(record.ebay_variant_ids)
            for variant in record.ebay_variant_ids:
                if variant.is_active_variant:
                    total_active += 1
            record.count_active_variants = total_active
        else:
            record.count_exported_variants = 0
            record.count_active_variants = 0

    @api.depends('category_id1', 'category_id2')
    def _compute_get_ebay_features(self):
        """
        Calculates auto pay enabled, return policy and digital good delivery
        :return: get auto pay enabled, return policy and digital good delivery
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        for record in self:
            category_id1 = record.category_id1
            category_id2 = record.category_id2
            if category_id1 or category_id2:
                self.get_category_condition_enabled(record, category_id1, category_id2)
                auto_pay_enabled1 = (category_id1 and category_id1.auto_pay_enabled)
                auto_pay_enabled2 = (category_id2 and category_id2.auto_pay_enabled)
                set_return_policy1 = (category_id1 and category_id1.set_return_policy)
                set_return_policy2 = (category_id2 and category_id2.set_return_policy)
                dig_gd_del_en1 = (category_id1 and category_id1.digital_good_delivery_enabled)
                dig_gd_del_en2 = (category_id2 and category_id2.digital_good_delivery_enabled)
                record.auto_pay_enabled = auto_pay_enabled1 or auto_pay_enabled2 or False
                record.set_return_policy = set_return_policy1 or set_return_policy2 or False
                record.digital_good_delivery_enabled = dig_gd_del_en1 or dig_gd_del_en2 or False

    @staticmethod
    def get_category_condition_enabled(record, category_id1, category_id2):
        """
        Set condition enabled for categories
        :param record: eBay categories record.
        :param category_id1: eBay parent category
        :param category_id2: eBay child category
        """
        if len(record.ebay_variant_ids) > 1:
            condition_enabled1 = (category_id1 and category_id1.condition_enabled)
            condition_enabled2 = (category_id2 and category_id2.condition_enabled)
            record.condition_enabled = condition_enabled1 or condition_enabled2 or False
        else:
            record.condition_enabled = False

    def _search_ebay_active_product(self, operator, values):
        """
        Search eBay active products
        :param operator: Operator to be used in searching records
        :param values: values to be searched
        :return: active product template ids
        """
        product_tmpl_id = []
        if operator == '!=':
            self._cr.execute("""SELECT ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Active'""")
            ebay_product_templates = self._cr.dictfetchall()
        elif operator == '=':
            self._cr.execute("""SELECT distinct ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Ended'
            except (SELECT distinct ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Active')""")
            ebay_product_templates = self._cr.dictfetchall()
        for ebay_product_template in ebay_product_templates:
            product_tmpl_id.append(ebay_product_template.get('ebay_product_tmpl_id'))
        return [('id', 'in', list(set(product_tmpl_id)))]

    def _compute_get_ebay_active_product(self):
        for ebay_variant in self:
            ebay_prod_list = self.env[_EBAY_PRODUCT_LISTING].search([
                ('ebay_product_tmpl_id', '=', ebay_variant.id), ('state', '=', 'Active')], order='id desc', limit=1)
            ebay_variant.ebay_active_listing_id = ebay_prod_list.id if ebay_prod_list else False

    def prepare_product_dict(self, ebay_product_template, instance, publish_in_ebay, schedule_time):
        """
        Prepares Dictionary for export product in eBay.
        :param ebay_product_template: eBay Product Template object
        :param instance: Current instance of eBay
        :param publish_in_ebay: True if product is published in eBay else False
        :param schedule_time: Time at which product will export to eBay.
        :param listing_type: listing_type
        :return: dictionary of eBay Product parameters for export
        """
        sub_dict = {}
        if ebay_product_template.is_immediate_payment:
            sub_dict = {'AutoPay': ebay_product_template.is_immediate_payment}
        if instance.seller_id.ebay_plus:
            sub_dict.update({'eBayPlus': True})
        sub_dict = self.prepare_condition_description_dict(sub_dict, ebay_product_template,
                                                           ebay_product_template.category_id1)
        if ebay_product_template.count_total_variants > 1:
            template_description = ebay_product_template.description or ebay_product_template.name or ''
            # if template_description == '<p><br></p>':
            #     template_description = ''
            # prod_desc = (html.escape(str(template_description)).encode("utf-8")).decode('iso-8859-1')
            prod_desc = Markup('<![CDATA[{0}]]>').format(template_description)
            sub_dict.update({'Description': prod_desc})
        if ebay_product_template.digital_good_delivery_enabled:
            sub_dict.get('DigitalGoodInfo', {}).update({'DigitalDelivery': ebay_product_template.digital_delivery})
        # Use to identify listed location of the product in eBay
        sub_dict = self.prepare_ebay_item_locations_parameters_dict(instance, sub_dict)
        title = Markup('<![CDATA[{0}]]>').format(ebay_product_template.name)
        # (html.escape(ebay_product_template.name).encode("utf-8")).decode('iso-8859-1')
        sub_dict.update({
            'CategoryMappingAllowed': True,
            'Title': title,
            'ListingDuration': ebay_product_template.ebay_listing_duration,
            'ListingType': ebay_product_template.listing_type,
            'Currency': instance.pricelist_id.currency_id.name,
            'DispatchTimeMax': ebay_product_template.hand_time,
        })
        sub_dict = self.prepare_ebay_categories_values(sub_dict, ebay_product_template)
        sub_dict = self.prepare_ebay_attributes_brand_mpn_dict(ebay_product_template, sub_dict)
        sub_dict = self.prepare_ebay_seller_profiles_dict(ebay_product_template, sub_dict)
        if ebay_product_template.uuid_type:
            sub_dict.update({'UUID': ebay_product_template.uuid_type})
        sub_dict = self.prepare_ebay_scheduled_time(sub_dict, publish_in_ebay, schedule_time)
        return sub_dict

    @staticmethod
    def prepare_condition_description_dict(sub_dict, product, category_id1):
        """
         This method is used to check condition and condition description and prepare data in the dictionary accordingly.
        :param sub_dict: dictionary of parameters to be sent into eBay API
        :param product: eBay product object
        :param category_id1:  eBay Category object
        :return: dictionary with condition and condition description.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        condition = ""
        condition_description = ""
        if product.condition_id:
            condition = product.condition_id.condition_id
            if product.condition_description:
                condition_description = product.condition_description
            elif 'New' not in product.condition_id.name:
                condition_description = product.condition_id.name
        elif not product.condition_id and category_id1 and category_id1.ebay_condition_ids:
            product.condition_id = category_id1.ebay_condition_ids[0].id
            condition = product.condition_id.condition_id
        if condition:
            # condition_description = html.escape(condition_description)
            # (condition_description.encode("utf-8")).decode("iso-8859-1")
            condition_description = Markup('<![CDATA[{0}]]>').format(condition_description)
            sub_dict.update({
                'ConditionDescription': condition_description,
                'ConditionID': condition})
        return sub_dict

    @staticmethod
    def prepare_ebay_item_locations_parameters_dict(instance, sub_dict):
        """
        This method is use to prepare dictionary for eBay item locations parameter.
        :param instance: eBay instance object.
        :param sub_dict: Dictionary of parameters to be sent to eBay.
        :return: Dictionary of parameters to be sent to eBay.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        item_location_country_id = instance.country_id or False
        item_location_name = instance.item_location_name or ''
        if item_location_country_id:
            sub_dict.update({'Country': item_location_country_id.code or ''})
        if instance and instance.post_code:
            sub_dict.update({'PostalCode': instance.post_code})
        if item_location_name:
            sub_dict.update({'Location': item_location_name})
        return sub_dict

    @staticmethod
    def prepare_ebay_categories_values(sub_dict, ebay_product_template):
        """
        Update eBay categories to the dictionary of parameters to be sent to eBay.
        :param sub_dict: Dictionary of parameters to be sent to eBay.
        :param ebay_product_template: eBay product template object
        :return: Dictionary of parameters to be sent to eBay.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        cat1_id = ebay_product_template.category_id1
        cat2_id = ebay_product_template.category_id2
        if cat1_id.ebay_category_id and not cat1_id.ebay_condition_ids:
            cat1_id.get_item_conditions()
        store_categ1 = ebay_product_template.store_categ_id1
        store_categ2 = ebay_product_template.store_categ_id2
        if cat1_id.ebay_category_id:
            sub_dict.update({'PrimaryCategory': {"CategoryID": [cat1_id.ebay_category_id]}})
        if cat2_id.ebay_category_id:
            sub_dict.update({'SecondaryCategory': {"CategoryID": [cat2_id.ebay_category_id]}})
        if store_categ1 or store_categ2:
            sub_dict.update({'Storefront': {}})
            if store_categ1:
                store_categ1_name = Markup('<![CDATA[{0}]]>').format(store_categ1.name)
                # store_categ1_name = html.escape(store_categ1.name).encode("utf-8")
                sub_dict.get('Storefront').update({
                    "StoreCategoryID": store_categ1.ebay_category_id,
                    'StoreCategoryName': store_categ1_name})
            if store_categ2:
                # store_categ2_name = html.escape(store_categ2.name).encode("utf-8")
                store_categ2_name = Markup('<![CDATA[{0}]]>').format(store_categ2.name)
                sub_dict.get('Storefront').update({
                    "StoreCategory2ID": store_categ2.ebay_category_id,
                    'StoreCategory2Name': store_categ2_name})
        return sub_dict

    @staticmethod
    def prepare_ebay_attributes_brand_mpn_dict(ebay_product_template, sub_dict):
        """
        Update eBay attributes brand and mpn to the dictionary to be sent to eBay.
        :param ebay_product_template: eBay product template object
        :param sub_dict: Dictionary to be sent to eBay.
        :return: Dictionary to be sent to eBay.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        brand_name = mpn_name = ''
        item_specifics_list = []

        for attribute in ebay_product_template.attribute_ids:
            attribute_name = attribute.attribute_id.name
            attribute_value = attribute.value_id.name
            if attribute.attribute_id.is_brand:
                brand_name = attribute_value
                continue
            if attribute.attribute_id.is_mpn:
                mpn_name = attribute_value
                continue
            if attribute_name in ShippingPackageAttributes and not attribute.attribute_id.is_brand and not attribute.attribute_id.is_mpn:
                if 'ShippingPackageDetails' not in sub_dict:
                    sub_dict.update({'ShippingPackageDetails': {}})
                sub_dict.update({'ShippingPackageDetails': {attribute_name: attribute_value}})
            item_specifics_data = {'Name': attribute_name, 'Value': attribute_value}
            item_specifics_list.append(item_specifics_data)
        if brand_name and mpn_name:
            brand_mpn = [{'Name': 'Brand', 'Value': brand_name}, {'Name': 'MPN', 'Value': mpn_name}]
            item_specifics_list += brand_mpn

        sub_dict.update({'ProductListingDetails': {}})
        if item_specifics_list:
            sub_dict.update({'ItemSpecifics': {'NameValueList': item_specifics_list}})
        if brand_name and mpn_name:
            brand_and_mpn = {'Brand': brand_name, 'MPN': mpn_name}
            sub_dict.update({'ProductListingDetails': {'BrandMPN': brand_and_mpn}})
        else:
            sub_dict.update({'ProductListingDetails': {'BrandMPN': {'Brand': 'Unbranded', 'MPN': _NOT_APPLIED}}})
        return sub_dict

    @staticmethod
    def prepare_ebay_seller_profiles_dict(ebay_product_template, sub_dict):
        """
        This mehtod is use to update eBay seller profiles to the dictionary to be sent to eBay..
        :param sub_dict: Dictionary to be sent to eBay.
        :return: Dictionary to be sent to eBay.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        ebay_seller_shipping_policy = ebay_product_template.ebay_seller_shipping_policy_id
        ebay_seller_payment_policy = ebay_product_template.ebay_seller_payment_policy_id
        ebay_seller_return_policy = ebay_product_template.ebay_seller_return_policy_id
        if ebay_seller_payment_policy or ebay_seller_return_policy or ebay_seller_shipping_policy:
            sub_dict.update({'SellerProfiles': {}})
            if ebay_seller_payment_policy:
                sub_dict.get('SellerProfiles').update({
                    'SellerPaymentProfile': {'PaymentProfileID': ebay_seller_payment_policy.policy_id}})
            if ebay_seller_return_policy:
                sub_dict.get('SellerProfiles').update({
                    'SellerReturnProfile': {'ReturnProfileID': ebay_seller_return_policy.policy_id}})
            if ebay_seller_shipping_policy:
                sub_dict.get('SellerProfiles').update({
                    'SellerShippingProfile': {'ShippingProfileID': ebay_seller_shipping_policy.policy_id}})
        return sub_dict

    @staticmethod
    def prepare_ebay_scheduled_time(sub_dict, publish_in_ebay, schedule_time):
        """
        Update schedule time to the dictionary to be sent to eBay.
        :param sub_dict: Dictionary to be sent to eBay.
        :param publish_in_ebay: True or False.
        :param schedule_time: eBay product listing schedule time.
        :return: Dictionary to be sent to eBay.
        """
        date_time_format = "%Y-%m-%dT%H:%M:%S"
        if not publish_in_ebay:
            schedule_time = schedule_time.strftime(date_time_format)
            time_obj = time.gmtime(time.mktime(time.strptime(schedule_time, date_time_format)))
            schedule_time = time.strftime(date_time_format, time_obj)
            schedule_time = str(schedule_time) + '.000Z'
            sub_dict.update({"ScheduleTime": schedule_time})
        return sub_dict

    def prepare_variation_product_dict(self, ebay_product_template, instance, publish_in_ebay, schedule_time):
        """
        This mehtod is use to prepare dictionary for eBay product variants
        :param ebay_product_template:  eBay product template object
        :param instance:  instance of eBay
        :param publish_in_ebay:  True of product is published in eBay
        :param schedule_time: Time at which product will export to eBay.
        :return: Dictionary for product variant.
        Migration done by Haresh Mori @ Emipro on date 25 December 2021 .
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        sub_dict = self.prepare_product_dict(ebay_product_template, instance, publish_in_ebay, schedule_time)
        sub_dict.update({'Variations': {}})
        list_of_name_value_list = self.get_name_value_list(ebay_product_template.product_tmpl_id.attribute_line_ids)
        sub_dict.get('Variations').update({'VariationSpecificsSet': list_of_name_value_list})
        list_of_variation = []
        list_of_variation_pictures = []
        image_urls = []
        warehouse_ids = self.env['stock.warehouse'].browse(
            set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))
        for variant in ebay_product_template.ebay_variant_ids:
            stock = self.get_ebay_product_stock_ept(instance, [variant.product_id.id], warehouse_ids)
            variation = {}
            start_price = instance.pricelist_id._get_product_price(variant.product_id, 1.0)
            # default_code = (html.escape(variant.ebay_sku).encode("utf-8")).decode("iso-8859-1")
            default_code = Markup('<![CDATA[{0}]]>').format(variant.ebay_sku)
            variation_product_listing_details = self.get_ean_isbn_upc_dict(variant)
            variation_values = {
                'SKU': default_code, 'StartPrice': start_price, 'Quantity': int(stock[variant.product_id.id]),
                'VariationProductListingDetails': variation_product_listing_details
            }
            variation.update(variation_values)
            list_of_variation_specific = self.get_name_value_list(
                variant.product_id.product_template_attribute_value_ids, True)
            variation.update({'VariationSpecifics': list_of_variation_specific})
            list_of_variation.append(variation)
            image_urls = ebay_product_template.prepare_ebay_product_images_dict(variant, instance, image_urls)
        sub_dict.update({'PictureDetails': {'PictureURL': image_urls}})
        sub_dict.get('PictureDetails').update({'GalleryURL': image_urls})
        sub_dict.get('Variations').update({'variation': list_of_variation})
        ebay_attr = ebay_product_template.attribute_id.name or ''
        # (html.escape(ebay_attr).encode("utf-8")).decode("iso-8859-1")
        list_of_variation_pictures.append({
            'VariationSpecificPictureSet': {'PictureURL': list(set(image_urls))},
            'VariationSpecificName': Markup('<![CDATA[{0}]]>').format(ebay_attr)})
        sub_dict.get('Variations').update({'Pictures': list_of_variation_pictures})
        if instance.site_id:
            sub_dict.update({'Site': instance.site_id.name})
        return {'Item': sub_dict}

    @staticmethod
    def get_name_value_list(attribute_ids, is_variant=False):
        """
        Prepare name value list
        :param attribute_ids: eBay attribute ids
        :param is_variant: True or False
        :return: dictionary for name value list
        """
        list_of_name_value_list = []
        name_value_list = []
        for line in attribute_ids:
            attribute = line.attribute_id
            if is_variant:
                values = line.product_attribute_value_id.name
            else:
                values = [value.name for value in line.value_ids]
            simple_name = attribute.name or ""
            simple_name = simple_name.encode("utf-8").decode("iso-8859-1")
            name_value_list.append({'Name': simple_name, 'Value': values})
        list_of_name_value_list.append({'NameValueList': name_value_list})
        return list_of_name_value_list

    def prepare_individual_item_dict(self, ebay_product_template, variant, instance, publish_in_ebay, schedule_time):
        """
        Prepare dictionary for product without variant for the export product.
        :param ebay_product_template: eBay product template object
        :param variant: variant of eBay product
        :param instance: instance of eBay
        :param publish_in_ebay: True if product is published in eBay
        :param schedule_time:  Time at which product will be exported
        :return: Dictionary for individual product items
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        sub_dict = self.prepare_product_dict(ebay_product_template, instance, publish_in_ebay, schedule_time)
        default_code = variant.ebay_sku or variant.product_id.default_code
        if default_code:
            # (html.escape(default_code).encode("utf-8")).decode("iso-8859-1")
            sku = Markup('<![CDATA[{0}]]>').format(default_code)
            sub_dict.update({'SKU': sku})
        list_image_url = ebay_product_template.prepare_ebay_product_images_dict(variant, instance, [])
        sub_dict.update({'PictureDetails': {'PictureURL': list_image_url}})
        sub_dict.get('PictureDetails').update({'GalleryURL': list_image_url})
        # set the individual product description according to the dynamic description template
        product_description = self.prepare_ebay_product_description_parameter(variant, ebay_product_template)
        sub_dict.update({'Description': product_description})
        category_id1 = ebay_product_template.category_id1
        sub_dict = self.prepare_condition_description_dict(sub_dict, variant, category_id1)
        sub_dict.update({'ProductListingDetails': self.get_ean_isbn_upc_dict(variant)})
        site_id = instance.site_id
        if site_id:
            self.prepare_ebay_product_prices_to_export(sub_dict, instance.pricelist_id, variant, 'StartPrice')
            warehouse_ids = self.env['stock.warehouse'].browse(
                set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))
            stock_dict = self.get_ebay_product_stock_ept(instance, [variant.product_id.id], warehouse_ids)
            product_stock = int(stock_dict[variant.product_id.id])
            _logger.info("Export_update stock:%s" % product_stock)
            sub_dict.update({'Site': site_id.name, 'Quantity': product_stock})
        return {'Item': sub_dict}

    def prepare_ebay_product_images_dict(self, variant, instance, list_image_url):
        """
        Prepare dictionary for product images.
        :param variant: eBay product id
        :param instance: eBay instance id
        :param list_image_url: Dictionary of product images.
        :return: Dictionary of product images.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        product_images = variant.product_id.ept_image_ids
        for image in product_images:
            ebay_image_url = image.create_picture_url(instance)
            if ebay_image_url:
                _logger.info("Imageurl: %s" % ebay_image_url)
                list_image_url.append(ebay_image_url)
            else:
                log_line_obj = self.env["common.log.lines.ept"]
                message = "Uploaded image quality is not good: Image name:%s and variant SKU:%s" % (
                    image.name, variant.ebay_sku)
                log_line_obj.create_common_log_line_ept(message=message,
                                                        module='ebay_ept', ebay_product_tmpl_id=self.id,
                                                        model_name='ebay.product.template.ept',
                                                        log_line_type='fail', mismatch=True,
                                                        ebay_instance_id=instance.id)
        return list_image_url

    def prepare_ebay_product_description_parameter(self, variant, ebay_product_template):
        """
        Prepare dictionary of eBay product description.
        :param instance: eBay instance object
        :param variant: eBay product product object
        :param ebay_product_template:  eBay product template object
        :return: Dictionary of eBay product description.
        """
        template_description = ebay_product_template.description or ebay_product_template.name or ''
        # if template_description == '<p><br></p>':
        #     template_description = ''
        # prod_desc = (html.escape(str(template_description)).encode("utf-8")).decode('iso-8859-1')
        prod_desc = Markup('<![CDATA[{0}]]>').format(template_description)
        return prod_desc

    @staticmethod
    def update_description_with_dynamic_template(variant, attribute, product_description):
        """
        Update product description according to dynamic description template
        :param variant: product object
        :param attribute: product attribute object
        :param product_description: product description received from product
        :return: Updated product description
        """
        if getattr(variant.product_id, attribute.field_id.name):
            if attribute.field_id.ttype == 'many2one':
                value = getattr(variant.product_id, attribute.field_id.name)
                product_description = product_description.replace(attribute.text, str(value.name))
            else:
                value = getattr(variant.product_id, attribute.field_id.name)
                product_description = product_description.replace(attribute.text, str(value))
        else:
            product_description = product_description.replace(attribute.text, '')
        return product_description

    @staticmethod
    def get_ean_isbn_upc_dict(product):
        """
        This mehtod is use to get dictionary of EAN, ISBN and UPC
        :param product: eBay product object
        :return: Dictionary of EAN, ISBN and UPC
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        variation_product_listing_details = {}
        if product.ean13 or product.isbn_number or product.upc_number:
            if product.ean13:
                variation_product_listing_details.update({'EAN': product.ean13})
            if product.isbn_number:
                variation_product_listing_details.update({'ISBN': product.isbn_number})
            if product.upc_number:
                variation_product_listing_details.update({'UPC': product.upc_number})
        else:
            variation_product_listing_details = {
                'UPC': _NOT_APPLIED, 'ISBN': _NOT_APPLIED, 'EAN': _NOT_APPLIED
            }
        return variation_product_listing_details

    @staticmethod
    def prepare_ebay_product_prices_to_export(sub_dict, instance_config_pricelist_id, variant,
                                              ebay_config_tmpl_price_name):
        """
        Prepare dictionary for eBay product prices
        :param sub_dict: Dictionary to be sent to eBay.
        :param ebay_config_tmpl_price_id: eBay template price object
        :param variant: eBay product object.
        :param ebay_config_tmpl_price_name:  eBay template price name
        :return: Dictionary to be sent to eBay.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        product_price = instance_config_pricelist_id._get_product_price(variant.product_id, 1.0)
        _logger.info(
            "Product name: %s and SKU %s, Export_Update price: %s" % (variant.name, variant.ebay_sku, product_price))
        sub_dict.update({
            ebay_config_tmpl_price_name: {'#text': product_price,
                                          '@attrs': {'currencyID': instance_config_pricelist_id.currency_id.name}}})
        return sub_dict

    def export_individual_item(self, ebay_product_template, publish_in_ebay, schedule_time):
        """
        Creates individual item for eBay product variant and added into active listing if response is success
        :param ebay_product_template: eBay product template object
        :param publish_in_ebay: True if product is published in eBay else false
        :param schedule_time:  Time at which product will be exported into eBay.
        :return: True or error sku list
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        instance = ebay_product_template.instance_id
        ebay_variant = ebay_product_template.ebay_variant_ids
        add_items = {'AddItemRequestContainer': []}
        variant_ids = {}
        product_listing = self.search_existing_active_product_listing(ebay_product_template, ebay_variant, instance)
        if not product_listing:
            product_dict = self.prepare_individual_item_dict(ebay_product_template, ebay_variant, instance,
                                                             publish_in_ebay, schedule_time)
            product_dict.update({'MessageID': 1})
            add_items['AddItemRequestContainer'].append(product_dict)
            variant_ids.update({1: ebay_variant.id})
            try:
                results = self.call_add_or_update_items_api(add_items, instance, 'AddItems')
            except Exception as error:
                raise UserError(_(str(error.response.dict())))
                # log_line = log_line_obj.create_common_log_line_ept(message=str(error.response.dict()),
                #                                                    module='ebay_ept', ebay_instance_id=instance.id,
                #                                                    ebay_product_tmpl_id=ebay_product_template.id,
                #                                                    model_name='ebay.product.template.ept',
                #                                                    log_line_type='fail', mismatch=False)
                # log_line.message_post(body='Prepare dictionary data for export product:  ' + str(product_dict))
                # return False
            if not results:
                results = {}
            if results.get('Ack', False) in ["Success", "Warning"]:
                add_item_res = results.get('AddItemResponseContainer', [])
                add_item_resp = [add_item_res] if type(add_item_res) == dict else add_item_res
                for add_item in add_item_resp:
                    self.create_product_listing_and_update_fees_when_add_items(
                        add_item, variant_ids, ebay_product_template, instance.id, ebay_variant)
        return True

    @staticmethod
    def call_add_or_update_items_api(items, instance, api_name):
        """
        Call add or update items ebay API.
        :param items: Items received from eBay.
        :param instance: eBay instance object
        :param api_name: eBay API name
        :return: response received from eBay.
        """
        lang = instance.lang_id and instance.lang_id.code
        if lang:
            items.update({'ErrorLanguage': lang})
        trading_api = instance.get_trading_api_object()
        trading_api.execute(api_name, items)
        results = trading_api.response.dict()
        return results

    def create_product_listing_and_update_fees_when_add_items(self, add_item, variant_ids_dict, ebay_product_template,
                                                              instance_id, ebay_variant):
        """
        Create product listing and update fees when add items to eBay.
        :param add_item: add items request parameters dictionary.
        :param variant_ids_dict: eBay variant ids dictionary.
        :param ebay_product_template: eBay product template object
        :param instance_id: eBay instance id.
        :param ebay_variant: eBay product object
        """
        ebay_product_listing_obj = self.env[_EBAY_PRODUCT_LISTING]
        ebay_product_variant_obj = self.env['ebay.product.product.ept']
        if add_item.get('ItemID', False):
            message_id = add_item.get('CorrelationID', 1)
            variant_id = variant_ids_dict.get(int(message_id))
            variant = ebay_product_variant_obj.browse(variant_id)
            ebay_listing_duration = ebay_product_template.ebay_listing_duration
            listing_type = ebay_product_template.listing_type
            product_listing_values = self.get_values_for_product_listing(
                instance_id, add_item, ebay_product_template, listing_type,
                variant.id)
            product_listing_values.update({'listing_duration': ebay_listing_duration})
            ebay_product_listing_obj.create(product_listing_values)
        ebay_variant.ebay_product_tmpl_id.write({'exported_in_ebay': True})
        ebay_variant.write({'exported_in_ebay': True})
        self.update_fees_ept(add_item.get('Fees', {}).get('Fee'), ebay_variant.ebay_product_tmpl_id, ebay_variant)
        self._cr.commit()

    def export_variation_item(self, ebay_product_template, publish_in_ebay, schedule_time):
        """
        This method is use to creates product variant item of eBay.
        :param ebay_product_template:  eBay product template object
        :param publish_in_ebay:  True if product is published in eBay
        :param schedule_time:  Time at which product will be exported
        :return: True or error sku list
        Migration done by Haresh Mori @ Emipro on date 25 December 2021 .
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        instance = ebay_product_template.instance_id
        if ebay_product_template.product_listing_ids.filtered(
                lambda x: x.instance_id == instance and x.state == 'Active'):
            ebay_product_template.write({'exported_in_ebay': True})
            return True
        product_dict = self.prepare_variation_product_dict(ebay_product_template, instance, publish_in_ebay,
                                                           schedule_time)
        product_dict.update({'WarningLevel': 'High'})
        trading_api = instance.get_trading_api_object()
        try:
            result = trading_api.execute('AddFixedPriceItem', product_dict)
        except Exception as error:
            result = trading_api.response
            if result.dict().get('Ack') not in ["Success", "Warning"]:
                raise UserError(_(str(error)))
                # log_line = log_line_obj.create_common_log_line_ept(message=str(error),
                #                                                    module='ebay_ept', ebay_instance_id=instance.id,
                #                                                    ebay_product_tmpl_id=ebay_product_template.id,
                #                                                    model_name='ebay.product.template.ept',
                #                                                    log_line_type='fail', mismatch=False)
                # log_line.message_post(body='Prepare dictionary data for export product:  ' + str(product_dict))
                # return False
        if result.dict().get('Ack') in ["Success", "Warning"]:
            self.create_ebay_product_listing(instance, result.dict(), ebay_product_template, 'FixedPriceItem')
            ebay_product_template.write({'exported_in_ebay': True})
            ebay_product_template.ebay_variant_ids.write({'exported_in_ebay': True})
            warehouse_ids = self.env['stock.warehouse'].browse(
                set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))
            for variant in ebay_product_template.ebay_variant_ids:
                stock = self.get_ebay_product_stock_ept(instance, [variant.product_id.id], warehouse_ids)
                if stock[variant.product_id.id] > 0.0:
                    variant.write({'exported_in_ebay': True, 'is_active_variant': True})
            self.update_fees_ept(result.dict().get('Fees', {}).get('Fee'), ebay_product_template)
        return True

    def update_individual_item(self, ebay_product_template, publish_in_ebay, schedule_time):
        """
        This method is use to update eBay product values in eBay store without variant.
        :param ebay_product_template: eBay product template object
        :param publish_in_ebay: True if product is published in eBay
        :param schedule_time: Time at which product will be exported in eBay
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        instance = ebay_product_template.instance_id
        ebay_variant = ebay_product_template.ebay_variant_ids
        product_listing = self.search_existing_active_product_listing(ebay_product_template, ebay_variant, instance)
        if product_listing:
            product_dict = self.prepare_individual_item_dict(ebay_product_template, ebay_variant, instance,
                                                             publish_in_ebay, schedule_time)
            product_dict.update({'WarningLevel': 'High'})
            product_dict = self.update_product_item_dict(product_listing, product_dict)
            try:
                results = self.call_add_or_update_items_api(product_dict, instance, 'ReviseItem')
            except Exception as error:
                raise UserError(_(str(error.response.dict())))
                # log_line = log_line_obj.create_common_log_line_ept(message=str(error.response.dict()),
                #                                                    module='ebay_ept', ebay_instance_id=instance.id,
                #                                                    ebay_product_tmpl_id=ebay_product_template.id,
                #                                                    model_name='ebay.product.template.ept',
                #                                                    log_line_type='fail', mismatch=False)
                # log_line.message_post(body='Prepare dictionary data for update product:  ' + str(product_dict))
                # return False
            if results and results.get('Ack', False) in ["Success", "Warning"]:
                add_item_res = results.get('AddItemResponseContainer', [])
                add_item_resp = [add_item_res] if type(add_item_res) == dict else add_item_res
                for result in add_item_resp:
                    self.update_product_listing_and_fees_when_update_items(result, product_listing,
                                                                           ebay_product_template, instance.id,
                                                                           ebay_variant)
        return True

    @staticmethod
    def update_product_item_dict(product_listing, product_dict):
        """
        This method is use to update listing values in the dictionary of product item.
        :param product_listing: eBay product listing object
        :param product_dict: dictionary of product items
        :return: updated dictionary of product items
        """
        for product_listing_rec in product_listing:
            product_dict.get('Item', {}).update({'ItemID': product_listing_rec.name or ''})
        return product_dict

    def update_product_listing_and_fees_when_update_items(self, result, product_listing_record, ebay_product_template,
                                                          instance_id, ebay_variant):
        """
        This method is use to update product listing and fees after update items values into eBay store.
        :param result: response received from eBay.
        :param product_listing_record: eBay product listing object
        :param ebay_product_template: eBay product template object
        :param instance_id: eBay instance id
        :param ebay_variant: eBay product object
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        if result.get('ItemID', False):
            listing_type = ebay_product_template.listing_type
            product_listing_values = self.get_values_for_product_listing(instance_id, result, ebay_product_template,
                                                                         listing_type, ebay_variant.id)
            product_listing_record.write(product_listing_values)
        self.update_fees_ept(result.get('Fees', {}).get('Fee'), ebay_variant.ebay_product_tmpl_id, ebay_variant)

    @staticmethod
    def search_existing_active_product_listing(ebay_product_template, ebay_variant, instance):
        """
        Search existing active product listing.
        :param ebay_product_template: eBay product template object.
        :param ebay_variant: eBay product object.
        :param instance: eBay instance object
        :return: eBay product listing object.
        Migration done by Haresh Mori @ Emipro on date 24 December 2021 .
        """
        return ebay_product_template.product_listing_ids.filtered(
            lambda x: x.ebay_variant_id == ebay_variant and x.instance_id == instance and x.state == 'Active')

    def update_variation_item(self, ebay_product_template, publish_in_ebay, schedule_time):
        """
        This method is use to update product with variants values.
        :param ebay_product_template: eBay product template object
        :param publish_in_ebay: True if product is published in eBay
        :param schedule_time: Time at which product will be exported
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        instance = ebay_product_template.instance_id
        product_listing_record = ebay_product_template.product_listing_ids.filtered(
            lambda x: x.ebay_product_tmpl_id == ebay_product_template and
                      x.instance_id == instance and x.state == 'Active')
        if not product_listing_record:
            return False
        product_listing_record = product_listing_record[0]
        product_dict = self.prepare_variation_product_dict(ebay_product_template, instance, publish_in_ebay,
                                                           schedule_time)
        product_dict.get('Item', {}).update({'ItemID': product_listing_record.name or ''})
        product_dict.update({'WarningLevel': 'High'})
        trading_api = instance.get_trading_api_object()
        try:
            result = trading_api.execute('ReviseFixedPriceItem', product_dict)
        except Exception as error:
            result = trading_api.response.dict()
            if result.get('Ack') not in ["Success", "Warning"]:
                raise UserError(_(str(error)))
                # log_line = log_line_obj.create_common_log_line_ept(message=str(error),
                #                                                    module='ebay_ept', ebay_instance_id=instance.id,
                #                                                    ebay_product_tmpl_id=ebay_product_template.id,
                #                                                    model_name='ebay.product.template.ept',
                #                                                    log_line_type='fail', mismatch=False)
                # log_line.message_post(body='Prepare dictionary data for update product:  ' + str(product_dict))
                # return False
        if result.dict().get('Ack') in ["Success", "Warning"]:
            product_listing_values = self.get_values_for_product_listing(instance.id, result.dict(),
                                                                         ebay_product_template, 'FixedPriceItem', False)
            product_listing_record.write(product_listing_values)
            self.update_fees_ept(result.dict().get('Fees', {}).get('Fee'), ebay_product_template)
            warehouse_ids = self.env['stock.warehouse'].browse(
                set(instance.ebay_stock_warehouse_ids.ids + instance.warehouse_id.ids))
            for variant in ebay_product_template.ebay_variant_ids:
                stock = self.get_ebay_product_stock_ept(instance, [variant.product_id.id], warehouse_ids)
                variant.write({'is_active_variant': stock[variant.product_id.id] > 0.0})
        return True

    @staticmethod
    def get_ebay_errors_dict(ebay_product_template, ebay_error_sku_list, trading_api):
        """
        Prepare dictionary of eBay errors received when create/update product into eBay.
        :param ebay_product_template: eBay product template object
        :param ebay_error_sku_list: eBay errors dictionary.
        :param trading_api: eBay trading API object.
        :return: Dictionary of eBay errors.
        """
        variant_ids = ebay_product_template.ebay_variant_ids
        error_sku = ','.join(str(x.ebay_sku or x.product_id.default_code) for x in variant_ids)
        ebay_error_sku_list += [{error_sku: trading_api.response.dict()}]
        return ebay_error_sku_list

    def update_fees_ept(self, fees, ebay_product_template, variant=False):
        """
        This method is use to Update eBay Fees in the ebay product template.
        :param fees: dictionary of eBay fees
        :param ebay_product_template: eBay Product template object
        :param variant: True if product has variants or false
        """
        currency_obj = self.env['res.currency']
        fee_obj = self.env['ebay.fee.ept']
        for fee in fees:
            currency_name = fee.get('Fee', {}).get('_currencyID')
            currency_id = currency_obj.search([('name', '=', currency_name)], limit=1)
            value = fee.get('Fee', {}).get('value')
            name = fee.get('Name')
            domain = [('name', '=', name), ('value', '=', value), ('currency_id', '=', currency_id.id),
                      ('ebay_product_tmpl_id', '=', ebay_product_template.id)]
            if variant:
                domain.append(('ebay_variant_id', '=', variant.id))
            exist_fee = fee_obj.search(domain)
            if not exist_fee:
                fee_obj.create({'name': name, 'value': value, 'currency_id': currency_id.id,
                                'ebay_product_tmpl_id': ebay_product_template.id,
                                'ebay_variant_id': variant and variant.id or False
                                })
        return True

    def relist_products(self, ebay_product_template, instance, product_listing):
        """
        This method use to Relist products to eBay
        :param listing_type: listing type (chinese, fixed_price_item, lead_generation)
        :param ebay_product_template: eBay product template object
        :param instance: current instance of eBay
        :param product_listing: ebay product listing object
        """
        # log_line_obj = self.env["common.log.lines.ept"]
        product_dict = {}
        try:
            trading_api = instance.get_trading_api_object()
            product_dict.update({'Item': {'ItemID': str(product_listing.name)}})
            trading_api.execute('RelistFixedPriceItem', product_dict)
            results = trading_api.response.dict()
        except Exception as error:
            raise UserError(_(str(error)))
            # log_line = log_line_obj.create_common_log_line_ept(message=str(error),
            #                                                    module='ebay_ept', ebay_instance_id=instance.id,
            #                                                    ebay_product_tmpl_id=ebay_product_template.id,
            #                                                    model_name='ebay.product.template.ept',
            #                                                    log_line_type='fail', mismatch=False)
            # log_line.message_post(body='Prepare dictionary data for relist product:  ' + str(product_dict))
            # return False
        if results.get('Ack', False) in ["Success", "Warning"]:
            variant_id = product_listing.ebay_variant_id.id
            self.create_ebay_product_listing(instance, results,
                                             product_listing.ebay_product_tmpl_id,
                                             ebay_product_template.listing_type, variant_id)
            product_listing.ebay_product_tmpl_id.write({'exported_in_ebay': True})
            self.update_fees_ept(results.get('Fees', {}).get('Fee'), product_listing.ebay_product_tmpl_id)
        return True

    def cancel_products_listing(self, ebay_active_listing, ending_reason):
        """
        This method is use to Cancel product from eBay listing
        :param ebay_active_listing: eBay product active listing object
        :param ending_reason: reason to cancel product
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        product_listing = self.env["ebay.product.listing.ept"]
        instance = ebay_active_listing.instance_id
        item_id = ebay_active_listing.name
        utc_diff_time = datetime.utcnow() - datetime.now()
        try:
            trading_api = instance.get_trading_api_object()
            trading_api.execute('EndItem', {'ItemID': item_id, 'EndingReason': ending_reason})
            results = trading_api.response.dict()
            listing_end_time = results.get('EndTime', False)
            end_tm = self.env['ebay.instance.ept'].odoo_format_date(listing_end_time)
            listing_end_time = datetime.strptime(end_tm, '%Y-%m-%d %H:%M:%S') - utc_diff_time
            ebay_end_listing_time = str(listing_end_time)[:19]
            ebay_active_listing.write({
                'is_cancel': True, 'cancel_listing': True, 'state': 'Ended',
                'ending_reason': ending_reason, 'end_time': ebay_end_listing_time})
            variant_active_listing = product_listing.search([('name', '=', item_id), ('state', '=', 'Active'),
                                                             ('instance_id', '=', instance.id)])
            if variant_active_listing:
                variant_active_listing.write({
                    'is_cancel': True, 'cancel_listing': True, 'state': 'Ended',
                    'ending_reason': ending_reason, 'end_time': ebay_end_listing_time})
        except Exception as error:
            raise UserError(str(error))
        return True

    def create_ebay_product_listing(self, instance, results, ebay_product_tmpl_id, listing_type, variant_id=False):
        """
        This method is use to creates an eBay Product listing.
        :param instance: eBay instance object
        :param results: response received from eBay.
        :param ebay_product_tmpl_id: eBay product template object
        :param listing_type: eBay listing type.
        :param variant_id: ebay variant id
        """
        ebay_product_listing_obj = self.env[_EBAY_PRODUCT_LISTING]
        product_listing_values = self.get_values_for_product_listing(instance.id, results, ebay_product_tmpl_id,
                                                                     listing_type, variant_id)
        ebay_product_listing_obj.create(product_listing_values)

    @staticmethod
    def get_item_listing_for_listing_url(instance, item_id):
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
            _logger.error('%s' % (str(error)))
        return item

    def get_values_for_product_listing(self, instance_id, item, ebay_product_tmpl_id, listing_type, variant_id=False):
        """
        Prepare values dictionary for product listing
        :param instance_id: eBay instance id
        :param item: item response from eBay API
        :param ebay_product_tmpl_id: eBay product Template object
        :param listing_type: eBay product listing type
        :param variant_id: eBay product id
        :param ebay_template_id: eBay product template id
        :return: dictionary of values for product listing
        Migration done by Haresh Mori @ Emipro on date 31 December 2021 .
        """
        listing_details = item.get('ListingDetails')
        if listing_details:
            start_time = listing_details.get('StartTime')
            end_time = listing_details.get('EndTime')
        else:
            start_time = item.get('StartTime')
            end_time = item.get('EndTime')
        item_id = item.get('ItemID', False)
        value = {
            'name': item.get('ItemID'),
            'instance_id': instance_id,
            'ebay_site_id': ebay_product_tmpl_id.site_id.id,
            'ebay_product_tmpl_id': ebay_product_tmpl_id.id,
            'start_time': start_time.split(".", 1)[0].replace("T", " "),
            'end_time': end_time.split(".", 1)[0].replace("T", " "),
            'listing_type': listing_type
        }
        if instance_id and item_id:
            instance = self.env['ebay.instance.ept'].browse(instance_id)
            new_vals = self.get_item_listing_for_listing_url(instance, item_id)
            new_listing_details = new_vals and new_vals.get('ListingDetails', False)
            if new_listing_details:
                value.update({'ebay_url': new_listing_details.get('ViewItemURL', False)})
        if variant_id:
            value.update({'ebay_variant_id': variant_id})
        return value

    def unlink(self):
        """
        Unlink variants from ebay product
        :return:
        """
        for record in self:
            if record.ebay_variant_ids:
                record.ebay_variant_ids.unlink()
        return super(EbayProductTemplateEpt, self).unlink()

    def get_ebay_product_stock_ept(self, instance, product_ids, warehouse):
        """
        Get stock based on stock type field of product.
        :param instance: This arguments relocates instance of amazon.
        :param product_ids: This arguments product listing id of odoo.
        :param warehouse:This arguments relocates warehouse of amazon.
        :return: This Method return product listing stock.
        """
        product_obj = self.env['product.product']
        product_listing_stock = False
        if product_ids:
            if instance.ebay_stock_field == 'free_qty':
                product_listing_stock = product_obj.get_free_qty_ept(warehouse, product_ids)
            elif instance.ebay_stock_field == 'virtual_available':
                product_listing_stock = product_obj.get_forecasted_qty_ept(warehouse, product_ids)
        return product_listing_stock

    def list_of_ebay_site_policy(self):

        """
        This method will return the action of removal order pickings.
        """
        ebay_site_policy = self.env[EBAY_SITE_POLICY].search([('instance_id', '=', self.instance_id.id)])
        action = {
            'domain': "[('id', 'in', " + str(ebay_site_policy.ids) + " )]",
            'name': 'Site Policy',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': EBAY_SITE_POLICY,
            'type': 'ir.actions.act_window',
        }
        return action

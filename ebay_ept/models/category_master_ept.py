#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to retrieve & store eBay categories
"""
import logging
import time
from odoo import models, fields, _
from odoo.exceptions import UserError
import requests

_logger = logging.getLogger(__name__)


class EbayCategoryMasterEpt(models.Model):
    """
    Describes about eBay Category.
    """
    _name = "ebay.category.master.ept"
    _description = "eBay Master Category"

    def _compute_complete_name(self):
        """
            Forms complete name of location from parent location to child location.
        """
        for cat in self:
            names = [cat.name]
            parent = True
            if cat.parent_id:
                rec = cat.parent_id
            else:
                parent = False
            while parent:
                names.append(rec.name)
                if not rec.parent_id:
                    parent = False
                    continue
                rec = rec.parent_id
                parent = rec.ebay_category_parent_id
            cat.ept_complete_name = '/'.join(reversed(names))

    name = fields.Char(string='Category Name', size=256, required=True, help="This field relocate eBay Category Name.")
    ept_complete_name = fields.Char(
        string='Name', compute=_compute_complete_name, store=False, help="This field relocate eBay Category.")
    ebay_category_id = fields.Char(string='Category ID', help="This field relocate eBay category id.")
    parent_id = fields.Many2one(
        "ebay.category.master.ept", string="Parent", help="This field relocate eBay parent id.")
    category_level = fields.Integer(string='eBay Category Level', help="This field relocate eBay category level.")
    ebay_category_parent_id = fields.Char(string='Parent Category', help="This field relocate eBay category level.")
    site_id = fields.Many2one('ebay.site.details', string='Site', help="This field relocate eBay Site.")
    active = fields.Boolean(
        string="Active Category", default=True, help="This field relocate check eBay category active ?.")
    attribute_ids = fields.One2many(
        'ebay.attribute.master', 'categ_id', string='Attributes', help="This field relocate eBay Attribute.")
    instance_id = fields.Many2one("ebay.instance.ept", string="Instance", help="This field relocate eBay site.")
    item_specifics = fields.Boolean(
        string="Item Specific Enabled", default=False, help="This field relocate check eBay Item Specific Enabled ?")
    condition_enabled = fields.Boolean(
        string="Item Condition Enabled", default=False, help="This field relocate check eBay Item Condition Enabled ?")
    variation_enabled = fields.Boolean(
        string="Variations Enabled", default=False, help="This field relocate check eBay Variations Enabled ?")
    leaf_category = fields.Boolean(
        string="Leaf eBayCategory", default=False, help="This field relocate check eBay Leaf Category ?")
    ebay_condition_ids = fields.One2many(
        "ebay.condition.ept", "category_id", string="eBay Condition", help="This field relocate eBay Condition ?")
    auto_pay_enabled = fields.Boolean(
        string="Auto Pay Enable", default=False, help="This Field relocate check Auto Pay Enable ?")
    set_return_policy = fields.Boolean(string="Return Policy", default=False, help="This Field relocate Return Policy.")
    best_offer_enabled = fields.Boolean(
        string="Item Best Offer Enabled", default=False, help="This Field relocate check Item Best Offer Enabled ?")
    gallery_plus_enabled = fields.Boolean(
        string="Free Gallery Plus Enabled", default=False, help="This Field relocate check Free Gallery Plus Enabled ?")
    offer_accept_enabled = fields.Boolean(
        string="Best Offer Auto Accept Enabled", default=False,
        help="This Field relocate check Best Offer Auto Accept Enabled ?")
    handling_time_enabled = fields.Boolean(
        string="HandlingTimeEnabled", default=False, help="This Field relocate check Handling Time Enabled ?")
    paypal_required = fields.Boolean(
        string='PayPalRequired', default=False, help="This Field relocate check PayPal Required ?")
    digital_good_delivery_enabled = fields.Boolean(
        string="DigitalGoodDeliveryEnabled", default=False,
        help="This Field relocate check Digital Good Delivery Enabled ?")
    is_store_category = fields.Boolean(
        string="Is Store Category ?", default=False, help="This Field relocate check Is Store Category ?")

    def import_store_category(self, instances, level_limit=0, only_leaf_categories=True):
        """
        Imports eBay Store Category
        :param instances: ebay instances of User
        :param level_limit: store category level
        :param only_leaf_categories: import only leaf categories if True
        """
        store_category_ids = []
        for instance in instances:
            category_resp = self.call_ebay_categories_api(instance, level_limit, only_leaf_categories, 'GetStore')
            categories = []
            custom_category = category_resp.get('Store', {}).get('CustomCategories', {})
            if custom_category and custom_category.get('CustomCategory', []):
                if isinstance(custom_category.get('CustomCategory', []), list):
                    categories = custom_category.get('CustomCategory', [])
                else:
                    categories = [custom_category.get('CustomCategory', [])]
            store_category_ids = self.create_or_update_store_child_categories(instance, categories, store_category_ids)
        return store_category_ids

    def create_or_update_store_child_categories(self, instance, categories, store_category_ids):
        """
        Create or update eBay store child categories
        :param instance: eBay instance object
        :param categories: eBay categories
        :param store_category_ids: dictionary of store category ids
        :return: dictionary of store category ids
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .
        """
        count = 0
        for category in categories:
            _logger.info("Start process of store category ID: %s and name: %s " % (
                category.get('Name'), category.get('CategoryID')))
            count += 1
            if count == 50:
                self._cr.commit()
                count = 0
            store_category_ids = self.create_or_update_ebay_category(category, instance, store_category_ids, True)
            child_categories = category.get('ChildCategory', [])
            if not isinstance(child_categories, list):
                child_categories = [child_categories]
            for child_category in child_categories:
                store_category_ids = self.create_or_update_ebay_category(child_category, instance, store_category_ids)
                sub_child_categories = child_category.get('ChildCategory', [])
                if not isinstance(sub_child_categories, list):
                    sub_child_categories = [sub_child_categories]
                for sub_child_category in sub_child_categories:
                    store_category_ids = self.create_or_update_ebay_category(sub_child_category, instance,
                                                                             store_category_ids)
            _logger.info("End process of store category ID: %s and name: %s " % (
                category.get('Name'), category.get('CategoryID')))
        return store_category_ids

    @staticmethod
    def call_ebay_categories_api(instance, level_limit, only_leaf_categories, api_name):
        """
        Get all ebay categories and store categories using API.
        :param instance: eBay instance object
        :param level_limit: Category level limit
        :param only_leaf_categories: True if only get leaf categories from eBay.
        :param api_name: eBay API name
        :return: category response from eBay.
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        site_id = False
        if instance.site_id:
            site_id = instance.site_id.site_id
        trading_api = instance.get_trading_api_object()
        category_parameters = {'DetailLevel': 'ReturnAll'}
        if level_limit > 0:
            category_parameters.update({'LevelLimit': level_limit})
        if site_id:
            category_parameters.update({'CategorySiteID': site_id})
        if only_leaf_categories:
            category_parameters.update({'ViewAllNodes': 'false'})
        else:
            category_parameters.update({'ViewAllNodes': 'true'})
        try:
            trading_api.execute(api_name, category_parameters)
            category_response = trading_api.response.dict()
        except Exception as error:
            raise UserError(_('%s', str(error)))
        return category_response

    def create_or_update_ebay_category(self, categories_resp, instance, category_ids, parent_category=False):
        """
        Create or update eBay categories.
        :param categories_resp: Categories response received from eBay
        :param instance: eBay instance object
        :param category_ids: Dictionary of category ids
        :param parent_category: True if parent category or False
        :return: Dictionary of category ids
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .
        """
        category_name = categories_resp.get('Name')
        category_id = categories_resp.get('CategoryID')
        if parent_category:
            ebay_category = self.search_category_by_instance(category_id, instance.id)
        else:
            ebay_category = self.search_child_category(category_id, instance)
        if ebay_category:
            ebay_category.write({'name': category_name})
        else:
            ebay_category = self.create_category(category_name, category_id, instance, ebay_category)
        category_ids.append(ebay_category.id)
        return category_ids

    def search_category_by_instance(self, category_id, instance):
        """
        Search category by instance
        :param category_id: Category ID received from eBay API
        :param instance: Instance of eBay
        :return: eBAy category ept object
        """
        return self.search([('ebay_category_id', '=', category_id), ('instance_id', '=', instance)], limit=1)

    def create_category(self, name, category_id, instance, category_record):
        """
        Create a new store category for eBay.
        :param name: Category name
        :param category_id: category ID received from eBay.
        :param instance: Instance of eBay
        :param category_record: Parent category record
        :return: ebay category ept object
        """
        return self.create({
            'name': name, 'ebay_category_id': category_id,
            'site_id': instance.site_id and instance.site_id.id or False, 'instance_id': instance.id,
            'is_store_category': True, 'ebay_category_parent_id': category_record.ebay_category_id,
            'parent_id': category_record.id
        })

    def search_child_category(self, category_id, instance):
        """
        Search child category of given category
        :param category_id: Category ID received from eBay
        :param instance: Instance of eBay
        :return:
        """
        return self.search([
            ('ebay_category_id', '=', category_id), ('site_id', '=', instance.site_id.id),
            ('is_store_category', '=', True), ('instance_id', '=', instance.id)], limit=1)

    def import_category(self, instances, level_limit=0, only_leaf_categories=True, is_import_get_item_condition=False):
        """
        Import ebay categories into Odoo
        :param instances: ebay instances of User
        :param level_limit: category level
        :param only_leaf_categories: import only leaf categories if True
        :param is_import_get_item_condition: Import item conditions if True
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        category_ids = []
        for instance in instances:
            category_resp = self.call_ebay_categories_api(instance, level_limit, only_leaf_categories, 'GetCategories')
            categories = []
            if category_resp.get('CategoryArray', {}):
                # returns list of dictionary
                categories = category_resp['CategoryArray'].get('Category', [])
            if isinstance(categories, dict):
                categories = [categories]
            category_ids = self.create_update_category(categories, instance, is_import_get_item_condition)
        return category_ids

    def create_update_category(self, categories_response, instance, is_import_get_item_condition):
        """
        This method is use to create/update product category in ebay category layer.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 22 December 2021 .
        Task_id: 180142 - Import Categories
        """
        category_ids = []
        count = 0
        for category_response in categories_response:
            count += 1
            if count == 50:
                self._cr.commit()
                count = 0
            category_id = category_response.get('CategoryID')
            _logger.info("Start the processing of categoryid: %s and name: %s" % (
                category_id, category_response.get('CategoryName')))
            exist_category = self.search_category(category_id, instance)
            ebay_category_values = self.prepare_ebay_categories_dict(category_response, instance)
            if not exist_category:
                exist_category = self.create(ebay_category_values)
            else:
                exist_category.write(ebay_category_values)
            category_ids.append(exist_category.id)
            _logger.info("End the processing of categoryid: %s and name: %s" % (
                category_id, category_response.get('CategoryName')))
            if is_import_get_item_condition:
                _logger.info("Start the processing of item condition of category_id: %s and name: %s" % (
                    category_id, category_response.get('CategoryName')))
                exist_category.get_item_conditions(instance)
        return category_ids

    def search_category(self, category_id, instance):
        """
        Search category in eBay layer
        :param category_id: Category ID received from eBay API
        :param instance: Instance of eBay
        :return: ebay category ept object
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        return self.search([('ebay_category_id', '=', category_id), ('site_id', '=', instance.site_id.id)], limit=1)

    def prepare_ebay_categories_dict(self, category, instance):
        """
        Prepare eBay categories values dictionary.
        :param category: category response received from eBay.
        :param instance: eBay instance object.
        :return: Dictionary of eBay category values
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        parent_category = False
        category_id = category.get('CategoryID')
        category_parent_id = category.get('CategoryParentID')
        if category_id != category_parent_id:
            parent_category = self.search_category(category_parent_id, instance)
        return {
            'name': category.get('CategoryName'),
            'ebay_category_id': category_id,
            'site_id': instance.site_id.id if instance.site_id else False,
            'leaf_category': (category.get('LeafCategory', "false") == 'true'),
            'ebay_category_parent_id': category.get('CategoryParentID'),
            'category_level': category.get('CategoryLevel'),
            'auto_pay_enabled': category.get('AutoPayEnabled'),
            'best_offer_enabled': (category.get('BestOfferEnabled', "false") == 'true'),
            'parent_id': parent_category.id if parent_category else False,
            'instance_id': instance.id
        }

    def get_attributes(self, max_name_levels, max_value_per_name):
        """
        Get attributes of category
        :param max_name_levels: Maximum name level of attribute
        :param max_value_per_name: Maximum value Of attribute per name
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .

        Added change in method to get attributes and its value.
        @author: Neha Joshi @Emipro Technologies Pvt. Ltd. date: 29/09/2022
        Task id : 202082
        """
        if not self.instance_id:
            instance = self.env['ebay.instance.ept'].search([('site_id', '=', self.site_id.id)], limit=1)
        else:
            instance = self.instance_id
        if self.ebay_category_id and self.leaf_category and instance:
            results = self.call_get_ebay_attributes_api(instance)

            values = results.get('aspects')
            attributes = []
            if isinstance(values, list):
                attributes = [
                    {'localizedAspectName': val.get('localizedAspectName'), 'aspectValues': val.get('aspectValues')} for
                    val
                    in values]

            for attribute in attributes[:max_name_levels]:
                category_attribute = self.search_or_create_ebay_category_attribute(attribute.get('localizedAspectName'),
                                                                                   self.id)
                attribute_values = []
                if isinstance(attribute.get('aspectValues'), list):
                    attribute_values = [val.get('localizedValue', []) for val in attribute.get('aspectValues')]
                for attribute_value in attribute_values[:max_value_per_name]:
                    self.search_or_create_ebay_category_attribute_values(
                        attribute_value, category_attribute.id)
        return True

    def call_get_ebay_attributes_api(self, instance):
        """
        Call get eBay attributes using API
        :param instance: eBay instance object
        :return: response(Contains dict of attribute and its value)

        Added change in method to call taxonomy api.
        @author: Neha Joshi @Emipro Technologies Pvt. Ltd. date: 29/09/2022
        Task id : 202082
        """
        seller_id = instance.seller_id
        site_id = instance.site_id
        category_id = self.ebay_category_id
        category_tree_id = site_id.site_id
        url_domain = 'api.ebay.com' if seller_id.environment == 'is_production' else 'api.sandbox.ebay.com'
        url = "https://{url_domain}/commerce/taxonomy/v1/category_tree/{category_tree_id}/get_item_aspects_for_category?category_id" \
              "={category_id}".format(url_domain=url_domain, category_tree_id=category_tree_id, category_id=category_id)

        access_token = seller_id.oauth_access_token
        response = requests.get(url, headers={'Content-Type': 'application/x-www-form-urlencoded',
                                              'Authorization': 'Bearer %s' % access_token}).json()
        if response.get('errors'):
            access_token = seller_id.generate_access_token_for_taxonomy_api()
            response = requests.get(url, headers={'Content-Type': 'application/x-www-form-urlencoded',
                                                  'Authorization': 'Bearer %s' % access_token}).json()
        return response

    def search_or_create_ebay_category_attribute(self, attribute_name, category_id):
        """
        Search or create eBay category attributes
        :param attribute_name: eBay attribute name
        :param category_id: eBay category id
        :return: eBay attribute master object
        """
        attribute_master_obj = self.env['ebay.attribute.master']
        category_attribute = attribute_master_obj.search(
            [('name', '=', attribute_name), ('categ_id', '=', category_id)], limit=1)
        if not category_attribute:
            category_attribute = attribute_master_obj.create({'name': attribute_name, 'categ_id': category_id})
        return category_attribute

    def search_or_create_ebay_category_attribute_values(self, attribute_value, category_attribute_id):
        """
        Search or create eBay category attribute values
        :param attribute_value: eBAy attribute values
        :param category_attribute_id: eBay attribute id
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .
        """
        attribute_value_obj = self.env['ebay.attribute.value']
        category_attribute_value = attribute_value_obj.search(
            [('name', '=', attribute_value), ('attribute_id', '=', category_attribute_id)])
        if not category_attribute_value:
            attribute_value_obj.create({'name': attribute_value, 'attribute_id': category_attribute_id})

    def get_item_conditions(self, instance=False):
        """
        This method is use to get the item condition from eBay.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 22 December 2021 .
        Task_id: 180142 - Import Categories
        """
        if not instance and self.instance_id:
            instance = self.instance_id
        if not instance:
            instance = self.env['ebay.instance.ept'].search([('site_id', '=', self.site_id.id)], limit=1)
        if self.ebay_category_id and instance:
            category_results = self.get_item_conditions_api(instance)
            if category_results:
                cat_def = category_results.get('SiteDefaults', {})
                cat_val = category_results.get('Category', {})
                condition_values = cat_val.get('ConditionValues', False)
                self.update_ebay_category(self, cat_def, cat_val)
                if condition_values:
                    condition_values = condition_values.get('Condition', [])
                    if isinstance(condition_values, dict):
                        condition_values = [condition_values]
                    for condition_value in condition_values:
                        condition_name = condition_value.get('DisplayName', False)
                        condition_id = condition_value.get('ID', False)
                        self.search_or_create_ebay_category_conditions(condition_id, self.id, condition_name)
                    self.create_child_categories_conditions(condition_name)
        return True

    def get_item_conditions_api(self, instance):
        """
        Get category item conditions by calling eBay API.
        :param instance: eBay instance object
        :return: response received from eBay API.
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        trading_api = instance.get_trading_api_object()
        item_condition_parameters = {
            'ViewAllNodes': True,
            'DetailLevel': 'ReturnAll',
            'AllFeaturesForCategory': True,
            'CategoryID': self.ebay_category_id
        }
        time.sleep(0.01)
        try:
            trading_api.execute('GetCategoryFeatures', item_condition_parameters)
        except Exception as error:
            raise UserError(_(str(error)))
        return trading_api.response.dict()

    @staticmethod
    def update_ebay_category(category, cat_def, cat_val):
        """
        This Method relocate write existing category.
        :param category: This Argument relocate existing category.
        :param cat_def: This Argument relocate site default details.
        :param cat_val: This Argument relocate ebay category.
        :return: This Method return write existing category and return.
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        item_specifics_enable = cat_val.get('ItemSpecificsEnabled', False) or cat_def.get('ItemSpecificsEnabled', False)
        condition_enabled = cat_val.get('ConditionEnabled', False) or cat_def.get('ConditionEnabled', False)
        offer_accept_enable = cat_val.get('BestOfferAutoAcceptEnabled', False)
        offer_accept_enabled = offer_accept_enable or cat_def.get('BestOfferAutoAcceptEnabled', False)
        gallery_plus_en = cat_val.get('FreeGalleryPlusEnabled', False) or cat_def.get('FreeGalleryPlusEnabled', False)
        set_return_policy = cat_val.get("ReturnPolicyEnabled", False) or cat_def.get('ReturnPolicyEnabled', False)
        variation_enabled = cat_val.get("VariationsEnabled", False) or cat_def.get('VariationsEnabled', False)
        handling_time_enabled = cat_val.get("HandlingTimeEnabled", False) or cat_def.get('HandlingTimeEnabled', False)
        digital_good_delivery_enable = cat_val.get('DigitalGoodDeliveryEnabled', False)
        digital_good_delivery_enabled = digital_good_delivery_enable or cat_def.get('DigitalGoodDeliveryEnabled', False)
        paypal_required = cat_val.get("PayPalRequired", False) or cat_def.get('PayPalRequired', False)
        category.write({
            'item_specifics': (item_specifics_enable == 'Enabled'),
            'condition_enabled': (condition_enabled == 'Required'),
            'offer_accept_enabled': (offer_accept_enabled != 'false'),
            'gallery_plus_enabled': (gallery_plus_en != 'false'),
            'set_return_policy': (set_return_policy != 'false'),
            'variation_enabled': (variation_enabled == 'true'),
            'handling_time_enabled': (handling_time_enabled == 'true'),
            'digital_good_delivery_enabled': (digital_good_delivery_enabled != 'false'),
            'paypal_required': (paypal_required != 'false')
        })

    def search_or_create_ebay_category_conditions(self, condition_id, category_id, condition_name):
        """
        Search or create eBay category conditions.
        :param condition_id: eBay category condition id
        :param category_id: eBay category id
        :param condition_name: eBay category condition name
        Migration done by Haresh Mori @ Emipro on date 22 December 2021 .
        """
        ebay_condition_obj = self.env['ebay.condition.ept']
        if condition_name and condition_id:
            ebay_condition = ebay_condition_obj.search(
                [('condition_id', '=', condition_id), ('category_id', '=', category_id), ('name', '=', condition_name)],
                limit=1)
            if not ebay_condition:
                ebay_condition_obj.create(
                    {'name': condition_name, 'condition_id': condition_id, 'category_id': category_id})

    def create_child_categories_conditions(self, condition_name):
        """
        Search item conditions in child categories.
        If not found then create item condition for that child category
        :param condition_name: item condition name
        Migration done by Haresh Mori @ Emipro on date 23 December 2021 .
        """
        if not self.leaf_category and self.ebay_condition_ids:
            child_categories = self.search([('parent_id', '=', self.id)])
            for child_category in child_categories:
                for condition in self.ebay_condition_ids:
                    self.search_or_create_ebay_category_conditions(condition.condition_id, child_category.id,
                                                                   condition_name)

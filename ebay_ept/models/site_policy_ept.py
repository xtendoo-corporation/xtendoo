#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields, api


class EbaySitePolicy(models.Model):
    """
    Sync Ebay Policies from eBay to Odoo
    """
    _name = 'ebay.site.policy.ept'
    _description = "eBay Site Policy"
    name = fields.Char(string='Ebay Policy Name', readonly=True, help="eBay Site Policy name.")
    policy_id = fields.Char(string='Policy ID', readonly=True, help="eBay Site Policy ID.")
    policy_type = fields.Char(string='Type', readonly=True, help="eBay Site Policy Type.")
    short_summary = fields.Text(string='Summary', readonly=True, help="eBay Site Policy short summary.")
    instance_id = fields.Many2one(
        'ebay.instance.ept', string="Instance", readonly=True, help="This field relocate eBay Instance.")

    @api.model
    def sync_policies(self, instance):
        """
        Sync Ebay policies from eBay
        :param instance: instance of eBay
        :return: True
        """
        ebay_policies_ids = []
        result = self.get_user_preferences_from_ebay(instance)
        policies = self.retrieve_policies_from_ebay(result)
        out_of_stock_control_preference = result.get('OutOfStockControlPreference')
        if out_of_stock_control_preference == 'false':
            instance.write({'allow_out_of_stock_product': False})
        else:
            instance.write({'allow_out_of_stock_product': True})
        policy_ids = list(map(lambda p: p['ProfileID'], policies))
        existing_policies = self.search([('policy_id', 'not in', policy_ids), ('instance_id', '=', instance.id)])
        existing_policies.unlink()
        ebay_policies_ids = self.create_or_update_ebay_site_policies(policies, instance, ebay_policies_ids)
        return ebay_policies_ids

    @staticmethod
    def retrieve_policies_from_ebay(result):
        """
        Retrieve policies from eBay.
        :param result: Policies received from eBay.
        :return: dictionary of eBay policies received.
        """
        seller_profile_preferences = result.get('SellerProfilePreferences', {})
        supported_seller_profiles = seller_profile_preferences.get('SupportedSellerProfiles', {})
        policies = []
        if supported_seller_profiles:
            policies = supported_seller_profiles.get('SupportedSellerProfile', [])
        if not isinstance(policies, list):
            policies = [policies]
        return policies

    @staticmethod
    def get_user_preferences_from_ebay(instance):
        """
        Get User preferences by calling eBay GetUserPreferences API.
        :param instance: eBay instance object.
        :return: User preference response received from eBay.
        """
        trading_api = instance.get_trading_api_object()
        para = {
            'ShowSellerProfilePreferences': True,
            'ShowSellerReturnPreferences': True,
            'ShowOutOfStockControlPreference': True
        }
        trading_api.execute('GetUserPreferences', para)
        return trading_api.response.dict()

    def create_or_update_ebay_site_policies(self, policies, instance, ebay_policies_ids):
        """
        Create or update eBay site policies.
        :param policies: policies received from eBay.
        :param instance: eBay instance object
        :param ebay_policies_ids: Dictionary of eBay policy ids
        :return: Dictionary of eBay policies ids
        """
        if policies:
            for policy in policies:
                ebay_site_policy = self.search([('policy_id', '=', policy['ProfileID']), ('instance_id', '=', instance.id)])
                if not ebay_site_policy:
                    ebay_site_policy = self.create({
                        'policy_id': policy['ProfileID'],
                    })
                ebay_site_policy.write({
                    'name': policy['ProfileName'],
                    'policy_type': policy['ProfileType'],
                    'short_summary': policy['ShortSummary'] if 'ShortSummary' in policy else ' ',
                    'instance_id': instance.id
                })
                ebay_policies_ids.append(ebay_site_policy.ids) # changed id to ids by Tushal Nimavat at 11/05/2022
        return ebay_policies_ids

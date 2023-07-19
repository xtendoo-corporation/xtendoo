#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay credentials of seller.
"""
from odoo import models, fields, api


class EbayCredential(models.TransientModel):
    """
    Describes eBay credentials
    """
    _name = "ebay.credential"
    _description = "eBay Credential"
    dev_id = fields.Char('Dev ID', size=256, required=True, help="eBay Dev ID")
    app_id = fields.Char('App ID (Client ID)', size=256, required=True, help="eBay App ID")
    cert_id = fields.Char('Cert ID (Client Secret)', size=256, required=True, help="eBay Cert ID")
    server_url = fields.Char('Server URL', size=256, help="eBay Server URL")
    environment = fields.Selection([
        ('is_sandbox', 'Sandbox'), ('is_production', 'Production')], 'eBay Environment', required=True)
    auth_token = fields.Text('Token', help="eBay Token")

    @api.model
    def default_get(self, fields_list):
        """
        Set default values for eBay instance
        :param fields_list: fields to be update/change
        """
        ebay_seller_obj = self.env['ebay.seller.ept']
        ebay_seller = ebay_seller_obj.browse(self.env.context.get('active_id'))
        res = super(EbayCredential, self).default_get(fields_list)
        res.update({
            'dev_id': ebay_seller.dev_id, 'app_id': ebay_seller.app_id,
            'cert_id': ebay_seller.cert_id, 'server_url': ebay_seller.server_url,
            'environment': ebay_seller.environment, 'auth_token': ebay_seller.auth_token})
        return res

    def update_changes(self):
        """
        Update eBay credentials
        """
        ebay_seller_obj = self.env['ebay.seller.ept']
        ebay_seller = ebay_seller_obj.browse(self.env.context.get('active_id'))
        ebay_seller.write({
            'dev_id': self.dev_id, 'app_id': self.app_id, 'cert_id': self.cert_id,
            'server_url': self.server_url, 'environment': self.environment, 'auth_token': self.auth_token})
        ebay_seller.confirm()
        return True

    @api.onchange('environment')
    def onchange_environment(self):
        """
        Set eBay server url based on selected environment
        """
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'

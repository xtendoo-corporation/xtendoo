#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes configuration for eBay seller and sites.
"""
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api

_INTERVALTYPES = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class ResConfigEbaySeller(models.TransientModel):
    """
    Describes configuration for eBay seller
    """
    _name = 'res.config.ebay.seller'
    _description = "eBay Res Configuration Seller"

    name = fields.Char("Seller Name", help="Please enter the name of ebay seller!")
    dev_id = fields.Char('eBay Dev ID', size=256, required=True, help="Please enter 'Dev ID' provided by the ebay!")
    app_id = fields.Char('App ID (Client ID)', size=256, required=True,
                         help="Please enter the 'Client ID' or 'App ID' provided by the ebay!")
    cert_id = fields.Char('Cert ID (Client Secret)', size=256, required=True,
                          help="Please enter 'Cert ID' or 'Client Secret' provided by the ebay!")
    server_url = fields.Char('Server URL', size=256, help="Please specify the ebay server url!")
    environment = fields.Selection([('is_sandbox', 'Sandbox'), ('is_production', 'Production')], 'eBay Environment')
    auth_token = fields.Text('Token', help="Please enter the Auth Token generated in ebay!")
    country_id = fields.Many2one('res.country', string="Country")
    company_id = fields.Many2one('res.company', string="Company")

    @api.onchange('environment')
    def onchange_environment(self):
        """
        Set server URL based on selected environment
        """
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'

    def create_ebay_seller(self):
        """
        Creates eBay Seller
        """
        site_details_obj = self.env['ebay.site.details']
        ebay_import_export_obj = self.env['ebay.process.import.export']
        seller = self.env['ebay.seller.ept'].create({
            'name': self.name, 'dev_id': self.dev_id, 'app_id': self.app_id, 'cert_id': self.cert_id,
            'server_url': self.server_url, 'environment': self.environment, 'auth_token': self.auth_token,
            'country_id': self.country_id.id, 'company_id': self.company_id.id})
        seller.create_site_details()
        seller.confirm()
        site_detail = site_details_obj.search([('country_id', '=', self.country_id.id)])
        if site_detail:
            instance_ids = site_detail.search_and_create_ebay_instance(seller.id)
            ebay_import_export_obj.get_ebay_details(instance_ids, seller)
            # ebay_import_export_obj.ebay_get_user_preferences(instance_ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

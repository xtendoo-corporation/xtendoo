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


class ResConfigEbayInstance(models.TransientModel):
    """
    Describes configuration for eBay instance
    """
    _name = 'res.config.ebay.instance'
    _description = "eBay Res Configuration Instance"
    name = fields.Char("Instance Name")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    product_site_url = fields.Char('eBay Product Site URL', help="Product site URL.")
    country_id = fields.Many2one('res.country', string="Country")
    seller_id = fields.Many2one('ebay.seller.ept', string='Seller', help="Select eBay Seller Name listed in odoo")
    site_ids = fields.Many2many(
        'ebay.site.details', 'res_config_ebay_site_rel', 'res_ebay_id',
        'ebay_site_id', string="eBay Sites", help="List of eBay Sites.")
    allow_out_of_stock_product = fields.Boolean(
        string="Allow out of stock ?",
        help="When the quantity of your Good 'Til Cancelled listing reaches zero,"
             " the listing remains active but is hidden from search until"
             " you increase the quantity. You may also qualify for certain fee credits",
        default=True)

    @api.onchange('seller_id')
    def onchange_seller_id(self):
        """
        Set domain for site ids when change eBay seller.
        """
        active_seller = self.seller_id
        ebay_active_seller = self.env['ebay.seller.ept'].browse(active_seller.id)
        site_id = ebay_active_seller.instance_ids.site_id.ids
        site_ids = self.env['ebay.site.details'].search([('id', 'not in', site_id)])
        return {'domain': {'site_ids': [('id', 'in', site_ids.ids)]}}

    def create_ebay_sites(self):
        """
        Creates eBay site if eBay site is not available.
        Added Condition for check the archive site is available or not if available then also not create the duplicate site.
        Last Updated on : 23_03_2021,
        Modify by = Harsh Parekh
        """
        ebay_instance_obj = self.env['ebay.instance.ept']
        instace_ids = ebay_instance_obj
        ebay_import_export_obj = self.env['ebay.process.import.export']
        if self.site_ids:
            self.site_ids.search_and_create_ebay_instance(self.seller_id.id)
        ebay_import_export_obj.get_ebay_details(instace_ids, self.seller_id)
        action = ebay_import_export_obj.ebay_get_user_preferences(instace_ids)
        return action

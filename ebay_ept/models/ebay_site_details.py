#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for ebay site details
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError

EBAY_SITE_COUNTRIES = {
    '0': 'US', '2': 'CA', '3': 'GB', '77': 'DE', '15': 'AU', '71': 'FR', '100': 'US',
    '101': 'IT', '146': 'NL', '186': 'ES', '203': 'IN', '201': 'HK', '216': 'SG', '207': 'MY',
    '211': 'PH', '210': 'CA', '212': 'PL', '123': 'BE', '23': 'BE', '16': 'AT', '193': 'CH', '205': 'IE'}


class EbaySiteDetails(models.Model):
    """
    Describes eBay Site Details
    """
    _name = "ebay.site.details"
    _description = "eBay Site Details"

    name = fields.Char(string="Site Name", size=256, required=True, help="eBay Site Name.")
    site_id = fields.Char(string='Site ID', size=256, required=True, help="eBay Site Id.", )
    country_id = fields.Many2one("res.country", "Country")

    @api.model
    def get_site_details(self, details):
        """
        Create site details if not else returns eBay site details
        :param details: site details received from eBay
        """
        country_obj = self.env['res.country']
        for record in details:
            site_name = record.get('Site')
            site_id = record.get('SiteID')
            search_site = self.search([('site_id', '=', site_id), ('name', '=', site_name)])
            if not search_site:
                country_code = EBAY_SITE_COUNTRIES.get(site_id)
                country = country_obj.search([('code', '=', country_code)], limit=1)
                self.create({'name': site_name, 'site_id': site_id, 'country_id': country.id})
        return True

    def search_and_create_ebay_instance(self, seller_id):
        """
        This method is use to create an instance.
        """
        ebay_instance_obj = self.env['ebay.instance.ept']
        instance_ids = ebay_instance_obj
        seller = self.env['ebay.seller.ept'].browse(seller_id)
        for site in self:
            instance_exist = ebay_instance_obj.search([('seller_id', '=', seller_id), ('site_id', '=', site.id),
                                                       '|', ('active', '=', True), ('active', '=', False)])
            if instance_exist:
                raise UserError(_('Site already exist for %s with given Credential.', site.name))

            price_list_vals = site.prepare_pricelist_vals(seller)
            price_list = self.env['product.pricelist'].create(price_list_vals)
            warehouse_id = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id)], limit=1)
            instance_ids += ebay_instance_obj.create({
                'seller_id': seller_id,
                'name': seller.name + '_' + site.name,
                'site_id': site.id,
                'country_id': site.country_id.id,
                'pricelist_id': price_list.id,
                'warehouse_id': warehouse_id.id
            })
        return instance_ids

    def prepare_pricelist_vals(self, seller):
        """
        Prepare dictionary for pricelist
        :param seller: eBay seller object
        :param site: eBay instance object
        :return: Dictionary of pricelist
        """
        site_currency = self.country_id.currency_id
        if not site_currency.active:
            site_currency.active = True
        pricelist_vals = {
            'name': seller.name + '_' + self.name + " Pricelist(%s)" % seller.name,
            'discount_policy': 'with_discount',
            'company_id': seller.company_id.id,
            'currency_id': site_currency.id,
        }
        return pricelist_vals

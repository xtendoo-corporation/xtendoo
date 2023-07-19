#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for excluding shipping locations
"""
from odoo import models, fields, api


class EbayExcludeShippingLocations(models.Model):
    """
    Describes exclude shipping locations for eBay
    """
    _name = "ebay.exclude.shipping.locations"
    _description = "eBay Exclude Shipping Locations"

    name = fields.Char(string="Location Name", help="This field relocate eBay Location name.")
    loc_code = fields.Char(string="Location Code", help="This field relocate eBay Location Code.")
    region = fields.Char(string="Shipping Location Region", help="This field relocate eBay Region.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_shipping_ex_locations_rel', 'shipping_id', 'site_id', required=True,
        help="This field relocate eBay Site Ids.")

    @api.model
    def create_exclude_shipping_locations(self, details, instance):
        """
        Creates exclude shipping locations for eBay product
        :param details: details received from eBay
        :param instance: current instance of eBay
        """
        site_id = instance.site_id.id
        for info in details:
            loc_name = info.get('Description', False)
            loc_code = info.get('Location', False)
            region = info.get('Region', False)
            location = {'name': loc_name, 'loc_code': loc_code, 'region': region}
            record = self.search([('name', '=', loc_name), ('loc_code', '=', loc_code)])
            if not record:
                location.update({'site_ids': [(6, 0, [site_id])]})
                self.create(location)
            else:
                site_ids = list(set(record.site_ids.ids + [site_id]))
                record.update({'site_ids': [(6, 0, site_ids)]})
        return True

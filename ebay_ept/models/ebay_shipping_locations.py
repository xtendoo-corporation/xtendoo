#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for shipping locations
"""
from odoo import models, fields, api


class EbayShippingLocations(models.Model):
    """
    Created Shipping locations for eBay
    """
    _name = "ebay.shipping.locations"
    _description = "eBay Shipping Locations"

    name = fields.Char(
        string='Shipping Location', help="This field relocate eBay Shipping Locations name.")
    ship_code = fields.Char(
        string='Location Code', help="This field relocate eBay Shipping Locations description.")
    detail_version = fields.Char(
        string='Shipping Location Detail Version', help="This field relocate eBay Shipping Location Detail Version.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_shipping_locations_rel', 'shipping_id',
        'site_id', help="This field relocate eBay Site Ids.", required=True)

    @api.model
    def create_shipping_locations(self, details, instance):
        """
        Create shipping locations for eBay product
        :param details: details received from eBay
        :param instance: current instance of eBay
        """
        site_id = instance.site_id.id
        for info in details:
            ship_code = info.get('ShippingLocation', False)
            name = info.get('Description', False)
            detail_version = info.get('DetailVersion', False)
            ship_loc = {'name': name, 'ship_code': ship_code, 'detail_version': detail_version}
            record = self.search([('name', '=', name), ('ship_code', '=', ship_code)])
            if not record:
                ship_loc.update({'site_ids': [(6, 0, [site_id])]})
                self.create(ship_loc)
            else:
                site_ids = list(set(record.site_ids.ids + [site_id]))
                record.update({'site_ids': [(6, 0, site_ids)]})
        return True

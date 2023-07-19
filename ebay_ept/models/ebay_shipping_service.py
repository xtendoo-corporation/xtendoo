#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for ship settings details
"""
from odoo import models, fields, api


class EbayShippingService(models.Model):
    """
    Describes eBay Shipping Service
    """
    _name = "ebay.shipping.service"
    _description = "eBay Shipping Service"
    name = fields.Char('Shipping Description', required=True)
    ship_time = fields.Char('Shipping time')
    inter_ship = fields.Boolean('International shipping')
    ship_carrier = fields.Char('Shipping Carrier')
    ship_service = fields.Char('Shipping Service')
    ship_service_id = fields.Char('Shipping Service ID')
    ship_type1 = fields.Char('Shipping Type')
    ship_type2 = fields.Char('International Shipping Type')
    ship_detail_version = fields.Char('Shipping Detail Version')
    ship_category = fields.Char('Shipping Category')
    validate_for_sale_flow = fields.Boolean('Validate for Saling Flow')
    sur_chg_applicable = fields.Boolean('Surcharge Applicable')
    dimension_required = fields.Boolean('Dimensions Required')
    cost = fields.Float('Cost($)')
    additional = fields.Float('Each Additional($)')
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_shipping_service_rel', 'shipping_id', 'site_id', required=True)

    @api.model
    def shipping_service_create(self, shipping_service_details, instance):
        """
        Create Shipping Service for eBay instance
        :param shipping_service_details: Shipping service details received from eBay
        :param instance: current instance of eBay
        """
        site_id = instance.site_id.id
        for shipping_detail in shipping_service_details:
            shipping_service_values = self.prepare_shipping_service_values_dict(shipping_detail)
            ship_ser_id = shipping_detail.get('ShippingServiceID', False)
            shipping_service = self.env['ebay.shipping.service'].search([
                ('ship_service_id', '=', ship_ser_id)])
            if not shipping_service:
                shipping_service_values.update({'site_ids': [(6, 0, [site_id])]})
                self.create(shipping_service_values)
            else:
                site_ids = list(set(shipping_service.site_ids.ids + [site_id]))
                shipping_service_values.update({'site_ids': [(6, 0, site_ids)]})
                shipping_service.write(shipping_service_values)
        return True

    @staticmethod
    def prepare_shipping_service_values_dict(shipping_detail):
        """
        Prepare shipping service values dictionary.
        :param shipping_detail: Shipping details received from eBay
        :return: dictionary of shipping details.
        """
        inter_ship = shipping_detail.get('InternationalService', False)
        surcharge = shipping_detail.get('SurchargeApplicable', False)
        dimension = shipping_detail.get('DimensionsRequired', False)
        ship_ser_id = shipping_detail.get('ShippingServiceID', False)
        valid_for_sale = shipping_detail.get('ValidForSellingFlow', False)
        ship_type = shipping_detail.get('ServiceType', False)
        ship_type1 = ship_type2 = False
        if isinstance(ship_type, list) and ship_type:
            ship_type1 = ship_type[0]
            ship_type2 = ship_type[1] if len(ship_type) > 1 else False
        elif isinstance(ship_type, str):
            ship_type1 = ship_type
        return {
            'name': shipping_detail.get('Description', False),
            'ship_time': shipping_detail.get('ShippingTimeMax', False),
            'inter_ship': inter_ship and (inter_ship == 'true' or inter_ship is True),
            'ship_carrier': shipping_detail.get('ShippingCarrier', False),
            'ship_service': shipping_detail.get('ShippingService', False),
            'ship_type1': ship_type1, 'ship_type2': ship_type2,
            'sur_chg_applicable': surcharge and (surcharge == 'true' or surcharge is True),
            'dimension_required': dimension and (dimension == 'true' or dimension is True),
            'ship_service_id': ship_ser_id,
            'ship_detail_version': shipping_detail.get('DetailVersion', False),
            'ship_category': shipping_detail.get('ShippingCategory', False),
            'validate_for_sale_flow': valid_for_sale and (valid_for_sale == 'true' or valid_for_sale is True),
        }

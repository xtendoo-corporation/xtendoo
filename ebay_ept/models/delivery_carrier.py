#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Added new fields for delivery carrier.
"""
import importlib
import sys
from odoo import models, fields

importlib.reload(sys)
PYTHONIOENCODING = "UTF-8"


class DeliveryCarrier(models.Model):
    """
    Added new fields for delivery.carrier
    """
    _name = "delivery.carrier"
    _inherit = "delivery.carrier"
    ebay_code = fields.Char('eBay Carrier Code', size=64, required=False)
    shipping_service_ids = fields.Many2many(
        "ebay.shipping.service", 'shipping_service_delivery_carrier_rel',
        'delivery_carrier_id', 'shipping_id', string="Select Shipping Services")

#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for stock picking.
"""
from odoo import models, fields


class StockPicking(models.Model):
    """
    Describes eBay order stock picking
    """
    _inherit = "stock.picking"

    shipping_id = fields.Many2one('ebay.shipping.service', string="Shipping", default=False, copy=False)
    ebay_instance_id = fields.Many2one("ebay.instance.ept", string="eBay Site", default=False, copy=False)
    is_ebay_delivery_order = fields.Boolean("eBay Delivery Order", default=False, copy=False)
    updated_in_ebay = fields.Boolean("Updated In eBay", default=False, copy=False)

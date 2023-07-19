#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for eBay stock update history
"""
from odoo import models, fields


class EbayStockUpdateHistory(models.Model):
    """
    Describes history of eBay stock update.
    """
    _name = "ebay.stock.update.history"
    _description = "eBay Stock Update History"
    ebay_product_id = fields.Many2one(
        'ebay.product.product.ept',
        string="Product",
        help="This field relocates eBay Product"
    )
    ebay_sku = fields.Char(
        string="eBay Product Sku",
        related="ebay_product_id.ebay_sku",
        help="eBay Product Sku"
    )
    ebay_variant_id = fields.Char(
        string="Ebay Variant",
        related="ebay_product_id.ebay_variant_id",
        help="eBay Product Variant"
    )
    last_updated_qty = fields.Integer(
        "Last Updated Qty Of Product",
        help="Last Updated Quantity of Product"
    )
    listing_id = fields.Many2one(
        'ebay.product.listing.ept',
        string="Listing",
        help="This field relocates eBay Product Listing"
    )

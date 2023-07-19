#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields to upload product image into eBay.
"""
from odoo import models, fields


class EbayProductImageEpt(models.Model):
    """storage_image_in_ebay
    Upload product images to ebay
    """
    _name = 'ebay.product.image.ept'
    _description = "eBay product Image"

    odoo_image_id = fields.Many2one(
        "common.product.image.ept", ondelete="cascade", string="Odoo Images", help="Odoo Images")
    ebay_variant_id = fields.Many2one(
        "ebay.product.product.ept", string="eBay Product variant", help="eBay Product variant")
    ebay_product_template_id = fields.Many2one(
        "ebay.product.template.ept", string="eBay Product Template", help="eBay Product Template")
    url = fields.Char(string="Image Url", help="External URL of image")
    sequence = fields.Integer(string="Image Sequence", help="Sequence of images.", index=True, default=10)
    instance_id = fields.Many2one('ebay.instance.ept', 'eBay Site', help="eBay Sites", required=True)
    image = fields.Image("Product Image", help="eBay Product Image")

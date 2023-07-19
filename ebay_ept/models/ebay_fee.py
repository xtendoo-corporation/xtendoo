#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay Fee details
"""
from odoo import models, fields


class EbayFee(models.Model):
    """Describes eBay Fee"""
    _name = "ebay.fee.ept"
    _description = "eBay Fee"
    name = fields.Char(" Fee Name")
    currency_id = fields.Many2one("res.currency", "Currency")
    value = fields.Float(" Fee Value")
    ebay_product_tmpl_id = fields.Many2one("ebay.product.template.ept", "Template")
    ebay_variant_id = fields.Many2one('ebay.product.product.ept', string='eBay Variant Name', readonly=True)

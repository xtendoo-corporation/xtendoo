#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay attributes master
"""
from odoo import models, fields


class EbayAttributeMaster(models.Model):
    """
    Ebay Attribute Master Class
    """
    _name = "ebay.attribute.master"
    _description = "eBay Master Attributes"
    name = fields.Char('Attribute Name', required=True)
    categ_id = fields.Many2one('ebay.category.master.ept', 'Category', required=True)
    value_ids = fields.One2many('ebay.attribute.value', 'attribute_id', 'Attribute Values')
    is_brand = fields.Boolean("Is Brand Attribute",
                              help="Let system know that this is Brand attributes of specific category")
    is_mpn = fields.Boolean("Is MPN Attribute", help="Let system know that this is MPN attributes of specific category")

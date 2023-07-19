#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay attributes values
"""
from odoo import models, fields


class EbayAttributeValue(models.Model):
    """
    Ebay Attribute Value Class
    """
    _name = 'ebay.attribute.value'
    _description = "eBay Attribute Values"
    name = fields.Char('Attribute Value', required=True)
    attribute_id = fields.Many2one('ebay.attribute.master', 'Attribute Master', required=True)

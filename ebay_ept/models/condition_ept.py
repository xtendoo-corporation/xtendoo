#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay category conditions
"""
from odoo import models, fields


class EbayConditionEpt(models.Model):
    """
    Define fields for ebay item conditions
    """
    _name = "ebay.condition.ept"
    _description = "eBay Condition"
    name = fields.Char('Condition Name', required=True)
    condition_id = fields.Char('Condition ID', required=True)
    category_id = fields.Many2one('ebay.category.master.ept', 'Category ID', required=True)

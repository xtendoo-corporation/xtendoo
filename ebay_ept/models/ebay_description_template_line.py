#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for eBay description template line
"""
from odoo import models, fields


class EbayDescriptionTemplateLine(models.Model):
    """
    Describes Ebay Description Template Line
    """
    _name = "ebay.description.template.line"
    _description = "eBay Description Template Line"
    text = fields.Char("Template Text", required=True, help="Text that you want to replace with specific value.")
    field_id = fields.Many2one(
        "ir.model.fields", string="Field", help="Select fields name of product",
        domain="[('model','in',['product.product','product.template']),"
               "('ttype','in',['char','float','text','binary','datetime','integer'])]")
    template_id = fields.Many2one("ebay.description.template", string="Template")

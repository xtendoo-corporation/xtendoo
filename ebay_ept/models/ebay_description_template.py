#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for eBay description template
"""
from odoo import models, fields


class EbayDescriptionTemplate(models.Model):
    """
    Describes Ebay Description Template
    """
    _name = "ebay.description.template"
    _description = "eBay Description Template"
    _order = 'id desc'
    name = fields.Char("Template Name", required=True, help="Name of your Template")
    line_ids = fields.One2many(
        "ebay.description.template.line", "template_id", string="Lines",
        help="Here you can define what to be replace with specific value")
    description = fields.Text("HTML Content", required=True)

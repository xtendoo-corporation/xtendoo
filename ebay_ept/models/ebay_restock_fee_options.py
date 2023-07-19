#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes restock fee options
"""
from odoo import models, fields


class EbayRestockFeeOptions(models.Model):
    """
    Describes Restock Fee Options
    """
    _name = "ebay.restock.fee.options"
    _description = "eBay Restock Fee Options"

    name = fields.Char(
        string="RestockingFeeValueOption", required=True, help="This field relocate eBay Restock Fee Options name.")
    description = fields.Char(
        "Restock Fee Description", required=True, help="This field relocate eBay Restock Fee Options description.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_refund_restock_fee_rel', 'refund_id',
        'site_id', help="This field relocate eBay Site Ids.", required=True)

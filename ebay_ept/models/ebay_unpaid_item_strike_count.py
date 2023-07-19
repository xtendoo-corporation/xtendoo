#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields


class EbayUnpaidItemStrikeCount(models.Model):
    """
    Get Unpaid Item Strike from eBay to Odoo.
    """
    _name = "ebay.unpaid.item.strike.count"
    _description = "eBay Unpaid Item Strike Count"

    name = fields.Char(
        string="Period", required=True, help="This field relocate eBay Unpaid Item Strike Count name.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_unpaid_strike_rel', 'feedback_id',
        'site_id', help="This field relocate eBay Site Ids.", required=True)

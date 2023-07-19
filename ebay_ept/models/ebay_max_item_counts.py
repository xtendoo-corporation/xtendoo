#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields


class EbayMaxItemCounts(models.Model):
    """
    Get Max item counts from eBay to Odoo
    """
    _name = "ebay.max.item.counts"
    _description = "eBay Max Item Count"

    name = fields.Char(string="MaximumItemCount", required=True, help="This field relocate eBay max item counts name.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_max_item_counts_rel', 'feedback_id', 'site_id',
        help="This field relocate eBay Site Ids.", required=True)

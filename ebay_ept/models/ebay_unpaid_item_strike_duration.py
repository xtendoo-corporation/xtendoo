#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields


class EbayUnpaidItemStrikeDuration(models.Model):
    """
    Get Unpaid Item Strike Duration from eBay to Odoo.
    """
    _name = "ebay.unpaid.item.strike.duration"
    _description = "eBay Unpaid Item Strike Duration"

    name = fields.Char(
        "MaximumUnpaidItemStrikesDuration", required=True,
        help="This field relocate eBay Unpaid Item Strike Duration Name.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_unpaid_st_dur_rel', 'feedback_id',
        'site_id', required=True, help="This field relocate eBay Site Ids.")
    description = fields.Char(
        string="Unpaid Item Description", help="This field relocate eBay Unpaid Item Strike Duration Description.")

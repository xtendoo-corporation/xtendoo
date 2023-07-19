#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields


class MinFeedbackScore(models.Model):
    """
    Get Minimum Feedback Score from eBay to Odoo.
    """
    _name = "item.feedback.score"
    _description = "Item Feedback Score"
    name = fields.Char(string="MinimumFeedbackScore", help="This is under item strikes")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_item_feed_score_rel', 'feedback_id',
        'site_id', help="This field relocate eBay Site Ids.", required=True)

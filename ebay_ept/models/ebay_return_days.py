#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes refund return days
"""
from odoo import models, fields


class EbayReturnDays(models.Model):
    """
    Describes Refund Days
    """
    _name = "ebay.return.days"
    _description = "eBay Return Days"

    name = fields.Char(
        string="ReturnsWithinOption", required=True, help="This field relocate eBay Return Days name.")
    description = fields.Char(
        string="Refund Days Description", required=True, help="This field relocate eBay Return Days description.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_return_days_rel', 'refund_id', 'site_id',
        help="This field relocate eBay Site Ids.", required=True)

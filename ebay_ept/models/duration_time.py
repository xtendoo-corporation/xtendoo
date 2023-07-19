#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields eBay duration time
"""
from odoo import models, fields


class DurationTime(models.Model):
    """
    Store ebay item duration time
    """
    _name = "duration.time"
    _description = "eBay Duration Time"
    name = fields.Char('Duration', size=64)
    type = fields.Selection([('FixedPriceItem', 'Fixed Price')],
                            string='Duration Type', help="eBay Product Listing Type")

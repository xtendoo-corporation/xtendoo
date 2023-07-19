#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for account move line
"""
from odoo import models, fields


class AccountMoveLine(models.Model):
    """
    Account invoice line for ebay
    """
    _inherit = 'account.move.line'
    payment_updated_in_ebay = fields.Boolean(
        string="Payment Updated In eBay ?", default=False, help="If True, Payment is updated in eBay")

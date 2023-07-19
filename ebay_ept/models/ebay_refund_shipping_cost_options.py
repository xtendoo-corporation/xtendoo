#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes shipping costs paid by options
"""
from odoo import models, fields


class EbayRefundShippingCostOptions(models.Model):
    """
    Describes Refund Shipping Cost Paid By Options
    """
    _name = "ebay.refund.shipping.cost.options"
    _description = "eBay Refund Shipping Cost Options"

    name = fields.Char(
        string="ShippingCostPaidByOption", required=True,
        help="This field relocate eBay Refund Shipping Cost Options name.")
    description = fields.Char(
        string="Refund Shipping Cost Description", required=True,
        help="This field relocate eBay Refund Shipping Cost Options Description.")
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_refund_shipping_cost_rel', 'refund_id',
        'site_id', help="This field relocate eBay Site Ids.", required=True)

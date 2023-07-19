#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IrCron(models.Model):
    """
    Describes new field for eBay Seller cron.
    """
    _inherit = 'ir.cron'

    ebay_seller_cron_id = fields.Many2one('ebay.seller.ept', string="eBay Cron Scheduler",
                                          help="eBay Seller Cron Scheduler")

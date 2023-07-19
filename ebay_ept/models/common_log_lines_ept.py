#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields and methods for common log lines
"""
from odoo import models, fields, api


class CommonLogLineEpt(models.Model):
    """
    Describes common log book line
    """
    _inherit = "common.log.lines.ept"
    ebay_order_data_queue_line_id = fields.Many2one(
        "ebay.order.data.queue.line.ept", string="eBay Order Queue Line", help="eBay Order data queue line")
    import_product_queue_line_id = fields.Many2one(
        "ebay.import.product.queue.line", string="Product Queue Line", help="eBay product data queue line")
    ebay_product_tmpl_id = fields.Many2one(comodel_name="ebay.product.template.ept", string="eBay Product Template")
    ebay_instance_id = fields.Many2one("ebay.instance.ept", string="Site", help="eBay Site")
    # ebay_seller_id = fields.Many2one("ebay.seller.ept", string="Seller", help="eBay Seller")

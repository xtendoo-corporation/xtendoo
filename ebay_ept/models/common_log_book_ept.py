#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for common log book.
"""
from odoo import models, fields


class CommonLogBookEpt(models.Model):
    """
    Describes Common log book
    """
    _inherit = "common.log.book.ept"
    ebay_instance_id = fields.Many2one("ebay.instance.ept", string="Site", help="eBay Site")
    ebay_seller_id = fields.Many2one("ebay.seller.ept", string="Seller", help="eBay Seller")

    def create_order_common_log_lines(self, message, order_ref, order_data_queue_line_id):
        """
        Create log line for order common log book.
        :param message: Message to be written into log line
        :param order_ref: order reference
        :param order_data_queue_line_id: order data queue line id
        """
        self.write({
            'log_lines': [(0, 0, {
                'message': message, 'order_ref': order_ref, 'ebay_order_data_queue_line_id': order_data_queue_line_id})]
        })

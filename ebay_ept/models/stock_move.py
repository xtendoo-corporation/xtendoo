#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for stock move.
"""
from odoo import models, fields


class StockMove(models.Model):
    """
    Describes eBay order stock move
    """
    _inherit = 'stock.move'
    ebay_instance_id = fields.Many2one('ebay.instance.ept', string='eBay Site')
    ebay_order_reference = fields.Char("eBay Order Ref", default=False, help="Order Reference provided by eBay")

    def _get_new_picking_values(self):
        """We need this method to set eBay Instance in Stock Picking"""
        res = super(StockMove, self)._get_new_picking_values()
        sale_line_id = self.sale_line_id
        if sale_line_id and sale_line_id.order_id and sale_line_id.order_id.ebay_instance_id:
            sale_order = sale_line_id.order_id
            if sale_order.ebay_instance_id:
                res.update({'ebay_instance_id': sale_order.ebay_instance_id.id, 'is_ebay_delivery_order': True})
        return res

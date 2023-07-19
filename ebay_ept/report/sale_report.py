#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    ebay_instance_id = fields.Many2one('ebay.instance.ept', 'eBay Sites', readonly=True)
    ebay_seller_id = fields.Many2one('ebay.seller.ept', 'eBay Seller', readonly=True)

    def _select_additional_fields(self):
        res = super(SaleReport, self)._select_additional_fields()
        res["ebay_instance_id"] = "s.ebay_instance_id"
        res["ebay_seller_id"] = "s.ebay_seller_id"
        return res

    def _group_by_sale(self):
        res = super(SaleReport, self)._group_by_sale()
        res += """, 
            s.ebay_instance_id, 
            s.ebay_seller_id"""
        return res

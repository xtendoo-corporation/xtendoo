#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay attributes matching
"""
from odoo import models, fields, api


class EbayAttributeMatching(models.Model):
    """
    Methods for matching ebay attribute
    """
    _name = "ebay.attribute.matching"
    _description = "eBay Matching Attributes"
    attribute_id = fields.Many2one('ebay.attribute.master', string='Attribute Name', required=True)
    value_id = fields.Many2one('ebay.attribute.value', string='Attribute Values', required=True)
    product_tmpl_id = fields.Many2one('ebay.product.template.ept', string='eBay product Template')

    @api.onchange("attribute_id")
    def onchange_attribute(self):
        """
        Changed attribute values for different categories
        :return: dictionary of domain
        """
        domain = {}
        category_id1 = self.product_tmpl_id.category_id1
        category_id2 = self.product_tmpl_id.category_id2
        if self.product_tmpl_id:
            attribute_ids = category_id1 and category_id1.attribute_ids.ids
            attribute_ids += category_id2 and category_id2.attribute_ids.ids
            domain['attribute_id'] = [('id', 'in', attribute_ids or [])]
        if self.attribute_id:
            value_ids = self.attribute_id.value_ids.ids
            domain['value_id'] = [('id', 'in', value_ids)]
        else:
            domain['value_id'] = [('id', 'in', [])]
            self.value_id = False
        return {'domain': domain}

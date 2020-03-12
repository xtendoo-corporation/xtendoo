# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime


class ProductCategory(models.Model):
    _inherit = "product.category"

    item_ids = fields.One2many('category.pricelist.item', 'product_tmpl_id', 'Pricelist Items')


class CategoryPricelistItem(models.Model):
    _name = "category.pricelist.item"
    _description = "Category Pricelist Item"

    categ_id = fields.Many2one(
        'product.category', 'Product Category', ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)

    percentaje = fields.Float(string='Percentaje', digits=0)

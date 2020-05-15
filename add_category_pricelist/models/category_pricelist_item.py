# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime

import logging

class CategoryPricelistItem(models.Model):
    _name = "category.pricelist.item"
    _description = "Category Pricelist Item"

    categ_id = fields.Many2one(
        'product.category',
        string='Category',
        ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise."
    )
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)

    percentaje = fields.Float(string='Percentaje', digits=0 )

    def get_sale_percent(self, product_id, pricelist_id):
        #return self.search_read({'fields': ['percentaje']},
         #   [['categ_id', '=', product_id.categ_id.id], ['pricelist_id', '=', pricelist_id.id]], limit=1)

        percent = self.search_read([['categ_id', '=', product_id.categ_id.id], ['pricelist_id', '=', pricelist_id.id]], {'percentaje'}, offset=0, limit=1, order=None)

        for percents in percent:
            return percents.get('percentaje')

        return 0.00





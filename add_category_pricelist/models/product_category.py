# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime

class ProductCategory(models.Model):
    _inherit = "product.category"

    #item_ids = fields.One2many('category.pricelist.item', 'pricelist_id', String='Pricelist Items')
    #item_ids = fields.One2many('category.pricelist.item', 'categ_id', string='Pricelist Items')

    categ_id = fields.One2many(
        'category.pricelist.item',
        'categ_id',
        string='Pricelist Items'
    )
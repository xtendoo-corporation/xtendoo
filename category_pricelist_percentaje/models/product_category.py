# Copyright 2020 Xtendoo - DDL
# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    #item_ids = fields.One2many('category.pricelist.item', 'pricelist_id', String='Pricelist Items')
    #item_ids = fields.One2many('category.pricelist.item', 'categ_id', string='Pricelist Items')

    categ_id = fields.One2many(
        'category.pricelist.item',
        'categ_id',
        string='Pricelist Items'
    )

# Copyright 2020 Xtendoo - DDL
# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class CategoryPricelistItem(models.Model):
    _name = "category.pricelist.item"
    _description = "Category Pricelist Item"

    categ_id = fields.Many2one(
        'product.category',
        string='Category',
        ondelete='cascade',
        help="Specify a product category."
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        required=True
    )
    percentage = fields.Float(
        string='Percentage',
        digits=0
    )

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
    percentaje = fields.Float(
        string='Percentaje',
        digits=0
    )

    def get_sale_percent(self, product_id, pricelist_id):
        percents = self.search_read([['categ_id', '=', product_id.categ_id.id],
                                     ['pricelist_id', '=', pricelist_id.id]],
                                     {'percentaje'}, offset=0, limit=1, order=None)

        for percent in percents:
            return percent.get('percentaje')

        return 0.00





# Copyright 2020 Xtendoo - DDL
# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""
from odoo import api, fields, models, _


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):

        print('product_id*********************************************************')
        product_id = self.product_id[0].id
        print(product_id)

        print('pricelist_id*******************************************************')
        pricelist_id = self.pricelist_id[0].id
        print(pricelist_id)

        self._cr.execute("SELECT percentaje FROM category_pricelist_item WHERE pricelist_id = %s", (pricelist_id,))
        data = self._cr.fetchall()

        percent = data[0][0]
        product_cost = 100

        if percent > 0.00:
            self.fixed_price = product_cost + ( product_cost * percent / 100 )

        super()._get_pricelist_item_name_price()
 """



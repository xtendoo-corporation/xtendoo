# Copyright 2020 Xtendoo - DDL
# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import logging

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        logging.info('PRICELIST')
        logging.info(self.pricelist_id)
        pricelist_id = self.pricelist_id[0].id

        self._cr.execute("SELECT percentaje FROM category_pricelist_item WHERE pricelist_id = %s", (pricelist_id,))
        data = self._cr.fetchall()

        percent = data[0][0]
        product_cost= 100

        if percent > 0.00:
            self.fixed_price = product_cost + ( product_cost * percent / 100 )

        super(PricelistItem,self)._get_pricelist_item_name_price()




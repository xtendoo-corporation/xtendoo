# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
import logging

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        logging.info('PRICELIST')
        logging.info(self.pricelist_id)
        pricelist_id=self.pricelist_id[0].id

        self._cr.execute("SELECT percentaje FROM category_pricelist_item WHERE pricelist_id = %s", (pricelist_id,))
        data = self._cr.fetchall()

        logging.info(data)

        super(PricelistItem,self)._get_pricelist_item_name_price()




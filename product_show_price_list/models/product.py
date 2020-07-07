# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pricelist_1 = fields.Float('First pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_2 = fields.Float('Second pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_3 = fields.Float('Third pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_4 = fields.Float('Fourth pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_5 = fields.Float('Fifth pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_6 = fields.Float('Sixth pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))
    pricelist_7 = fields.Float('Seventh pricelist', compute='_compute_price_list', store=False,
                               digits=dp.get_precision('Product Price'))

    def _compute_price_list(self):

        for product in self:
            _logger.info(product.item_ids)

            product.pricelist_1 = 0
            product.pricelist_2 = 0
            product.pricelist_3 = 0
            product.pricelist_4 = 0
            product.pricelist_5 = 0
            product.pricelist_6 = 0
            product.pricelist_7 = 0

            for product_item_id in product.item_ids:

                _logger.info("*"*80)
                _logger.info("product_item_id.pricelist_id.id")
                _logger.info(product_item_id.pricelist_id.id)

                if product_item_id.pricelist_id.name == 'Tarifa pública':
                    product.pricelist_1 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-12: TARIFA ALMACEN':
                    product.pricelist_2 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-10: TARIFA HUELVA':
                    product.pricelist_3 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-06: TARIFA PROFESIONALES':
                    product.pricelist_4 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-04: TARIFA PETIT&ASTUTO':
                    product.pricelist_5 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-01: TARIFA TIENDA':
                    product.pricelist_6 = product_item_id.fixed_price

                if product_item_id.pricelist_id.name == 'T-03: TARIFA MARIO FIALHO':
                    product.pricelist_7 = product_item_id.fixed_price






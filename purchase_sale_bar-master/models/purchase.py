# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bar_qty = fields.Float(string='Bar Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)

    no_change_bar_qty = True

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):
        _logger.info("*"*80)
        _logger.info(self.bar_qty)
        _logger.info(self.product_id.weight)
        _logger.info(self.bar_qty * self.product_id.weight)

        _logger.info("VALOR DEL FLAG***********************")
        _logger.info(self.no_change_bar_qty)

        if not self.no_change_bar_qty:
            _logger.info("SALIDA por flag***********************")
            self.no_change_bar_qty = True
            return

        if self.bar_qty != 0 and self.product_id.weight != 0:
            self.product_qty = self.bar_qty * self.product_id.weight

    @api.onchange('product_qty')
    def onchange_product_quantity(self):
        _logger.info("*"*80)
        _logger.info(self.product_qty)
        _logger.info("*"*80)

        self.no_change_bar_qty = False
        _logger.info("****ENCIENDO EL FLAG***********************")

        if self.product_qty == 0 or self.product_id.weight == 0:
            self.bar_qty = 0
        else:
            self.bar_qty = self.product_qty / self.product_id.weight

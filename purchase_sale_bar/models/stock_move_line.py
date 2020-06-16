from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    bar_qty = fields.Float(
        string='Bar Quantity', 
        digits=dp.get_precision('Product Unit of Measure')
    )

    change_bar_qty = True

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):

        _logger.info("*****CAMBIO EN bar_qty****************")
        _logger.info("*stock.move.bar_qty*")
        _logger.info(self.bar_qty)
        _logger.info("*product_id.weight*")
        _logger.info(self.product_id.weight)
        _logger.info("*self.bar_qty * self.product_id.weight*")
        _logger.info(self.bar_qty * self.product_id.weight)
        _logger.info("self.change_bar_qty")
        _logger.info(self.change_bar_qty)

        if not self.change_bar_qty:
            self.change_bar_qty = True
            return

        if self.bar_qty != 0 and self.product_id.weight != 0:
            _logger.info("self.quantity_done")
            _logger.info(self.qty_done)

            self.qty_done = self.bar_qty * self.product_id.weight

    @api.onchange('qty_done')
    def onchange_quantity_done(self):

        _logger.info("*****CAMBIO EN quantity_done****************")

        _logger.info("self.id")
        _logger.info(self.id)
        _logger.info("self.product_id")
        _logger.info(self.product_id)
        _logger.info("self.change_bar_qty")
        _logger.info(self.change_bar_qty)
        _logger.info("self.quantity_done")
        _logger.info(self.qty_done)
        _logger.info("self.product_id.weight")
        _logger.info(self.product_id.weight)
        _logger.info("self.bar_qty")
        _logger.info(self.bar_qty)

        self.change_bar_qty = True

        if self.qty_done == 0 or self.product_id.weight == 0:
            self.bar_qty = 0
        else:
            self.bar_qty = self.qty_done / self.product_id.weight

        _logger.info('BARRAS')
        _logger.info(self.bar_qty)

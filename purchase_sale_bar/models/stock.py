from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

#    bar_qty = fields.Float(
#        string='Bar Quantity', 
#        digits=dp.get_precision('Product Unit of Measure')
#    )

    bar_qty = fields.Float(
        string='Bar Quantity', 
        digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_bar_qty',
        store=True,
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

        #  if not self.change_bar_qty:
        #      self.change_bar_qty = True
        #      return

        if self.bar_qty != 0 and self.product_id.weight != 0:
            _logger.info("self.quantity_done")
            _logger.info(self.quantity_done)

            self.quantity_done = self.bar_qty * self.product_id.weight

    @api.onchange('quantity_done')
    def onchange_quantity_done(self):

        _logger.info("*****CAMBIO EN quantity_done****************")

        _logger.info("self.id")
        _logger.info(self.id)
        _logger.info("self.product_id")
        _logger.info(self.product_id)
        _logger.info("self.change_bar_qty")
        _logger.info(self.change_bar_qty)
        _logger.info("self.quantity_done")
        _logger.info(self.quantity_done)
        _logger.info("self.product_id.weight")
        _logger.info(self.product_id.weight)
        _logger.info("self.bar_qty")
        _logger.info(self.bar_qty)

        self.change_bar_qty = True

        if self.quantity_done == 0 or self.product_id.weight == 0:
            self.bar_qty = 0
        else:
            self.bar_qty = self.quantity_done / self.product_id.weight

        _logger.info('BARRAS')
        _logger.info(self.bar_qty)

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity, 
            reserved_quant=reserved_quant)
        bar_qty = self.purchase_line_id.bar_qty
        if bar_qty:
            vals['bar_qty'] = bar_qty
        return vals

#    @api.model
#    def create(self, vals):
#        move = super().create(vals)
#        bar_qty = move.purchase_line_id.bar_qty
#        if bar_qty:
#            move.bar_qty = bar_qty
#        return move

    @api.depends('purchase_line_id.bar_qty')
    def _compute_bar_qty(self):
        for move in self:
            bar_qty = move.purchase_line_id.bar_qty
            if bar_qty:
                move.bar_qty = bar_qty


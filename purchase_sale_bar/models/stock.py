from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    bar_qty = fields.Float(
        string='Bar Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):
        for record in self:
            _logger.info(record.bar_qty)
            if record.bar_qty != 0 and record.product_id.weight != 0:
                record.quantity_done = record.bar_qty * record.product_id.weight

    @api.onchange('quantity_done')
    def onchange_quantity_done(self):
        for record in self:
            _logger.info(record.quantity_done)
            if record.quantity_done == 0 or record.product_id.weight == 0:
                record.bar_qty = 0
            else:
                record.bar_qty = record.quantity_done / record.product_id.weight

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity,
            reserved_quant=reserved_quant)
        bar_qty = self.purchase_line_id.bar_qty
        if bar_qty:
            vals['bar_qty'] = bar_qty
        return vals

    @api.model
    def create(self, vals):
        move = super().create(vals)
        bar_qty = move.purchase_line_id.bar_qty
        if bar_qty:
            move.bar_qty = bar_qty
        return move

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

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):
        for record in self:
            if record.bar_qty != 0 and record.product_id.weight != 0:
                record.qty_done = record.bar_qty * record.product_id.weight

    @api.onchange('qty_done')
    def onchange_quantity_done(self):
        for record in self:
            if record.qty_done == 0 or record.product_id.weight == 0:
                record.bar_qty = 0
            else:
                record.bar_qty = record.qty_done / record.product_id.weight

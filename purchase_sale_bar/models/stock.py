from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class StockMove(models.Model):
    _inherit = "stock.move"

    bar_qty = fields.Float(
        string='Bar Quantity',
        digits=dp.get_precision('Product Unit of Measure')
    )

    change_bar_qty = True

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):
        # if not self.change_bar_qty:
        #     self.change_bar_qty = True
        #     return

        import logging
        logging.info("*"*80)
        logging.info(self.product_id)
        logging.info(self.product_id.weight)
        logging.info(self.bar_qty)

        if self.bar_qty != 0 and self.product_id.weight != 0:
            self.quantity_done = self.bar_qty * self.product_id.weight

    @api.onchange('quantity_done')
    def onchange_quantity_done(self):
        self.change_bar_qty = False

        if self.quantity_done == 0 or self.product_id.weight == 0:
            self.bar_qty = 0
        else:
            self.bar_qty = self.quantity_done / self.product_id.weight

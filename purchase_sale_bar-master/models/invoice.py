from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    bar_qty = fields.Float(string='Bar Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)

    change_bar_qty = True

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):

        _logger.info("*bar_qty*")
        _logger.info(self.bar_qty)
        _logger.info("*product_id.weight*")
        _logger.info(self.product_id.weight)
        _logger.info("*self.bar_qty * self.product_id.weight*")
        _logger.info(self.bar_qty * self.product_id.weight)

        _logger.info("VALOR DEL FLAG***********************")
        _logger.info(self.change_bar_qty)

        if not self.change_bar_qty:
            self.change_bar_qty = True
            return

        if self.bar_qty != 0 and self.product_id.weight != 0:
            self.quantity = self.bar_qty * self.product_id.weight

    @api.onchange('quantity')
    def onchange_quantity(self):

        self.change_bar_qty = False

        if self.quantity == 0 or self.product_id.weight == 0:
            self.bar_qty = 0
        else:
            self.bar_qty = self.quantity / self.product_id.weight


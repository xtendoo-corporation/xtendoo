from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    bar_qty = fields.Float(
        string='Bar Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.onchange('bar_qty')
    def onchange_bar_qty(self):
        for record in self:
            if record.bar_qty != 0 and record.product_id.weight != 0:
                record.quantity = record.bar_qty * record.product_id.weight

    @api.onchange('quantity')
    def onchange_quantity(self):
        for record in self:
            if record.quantity == 0 or record.product_id.weight == 0:
                record.bar_qty = 0
            else:
                record.bar_qty = record.quantity / record.product_id.weight

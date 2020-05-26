from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.multi
    def _write(self, values):
        res = super(SaleOrder, self)._write(values)
        if any(not line.lot_id and line.product_id.tracking == 'lot' for line in self.order_line):
            raise UserError(
                _('You can\'t store this document with empty lots')
                )
        return res

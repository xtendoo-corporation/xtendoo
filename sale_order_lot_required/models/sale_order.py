from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            for line in so.order_line:
                if not line.lot_id and line.product_id.tracking == 'lot':
                    raise UserError(
                        _('You can\'t store this line %s with empty lot') %
                        line.product_id.name
                        )

                product_lot_qty = self._product_lot_qty(so, line)
                if product_lot_qty < line.product_uom_qty:
                    raise UserError(
                        _('Not enough stock in lot %s, only %.2f for product : %s') %
                        (line.lot_id.name, product_lot_qty, line.product_id.name )
                    )
        return res

    def _product_lot_qty(self, so, line):
        if so.warehouse_id and line.product_id:
            quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', so.warehouse_id.lot_stock_id.id),
                ('product_id', '=', line.product_id.id),
                ('lot_id', '=', line.lot_id.id),
            ])
            if quants:
                return sum(quants.mapped('quantity'))
        return 0

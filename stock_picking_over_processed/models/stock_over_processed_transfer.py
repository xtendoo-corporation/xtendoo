# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = "stock.overprocessed.transfer"

    def action_confirm(self):
        self.ensure_one()
        if self.picking_id:
            moves = self.picking_id._get_overprocessed_stock_moves()
            for move in moves:
                if self.picking_id.sale_id:
                    move_line = self.picking_id.sale_id.order_line.filtered(
                        lambda l: l.product_id == move.product_id
                        and l.product_uom_qty == move.product_uom_qty
                    )
                    if move_line:
                        move_line.product_uom_qty = move.quantity_done

        return super().action_confirm()

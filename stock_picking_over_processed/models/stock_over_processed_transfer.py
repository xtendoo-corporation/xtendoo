# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class Picking(models.Model):
    _inherit = "stock.picking"

    def action_update_sale_order(self):
        moves = self._get_overprocessed_stock_moves()
        for move in moves:
            if self.sale_id:
                move_line = self.sale_id.order_line.filtered(
                    lambda l: l.product_id == move.product_id
                    and l.product_uom_qty == move.product_uom_qty
                )
                if move_line:
                    move_line.product_uom_qty = move.quantity_done

            move.product_uom_qty = move.quantity_done

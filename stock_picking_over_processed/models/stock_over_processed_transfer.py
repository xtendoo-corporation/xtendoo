# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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

# class StockMoveLine(models.Model):
#     _inherit = "stock.move.line"
#
#     @api.onchange('lot_id')
#     def _onchange_lot_id(self):
#         raise UserError("%s Lot changed" % self.lot_id.name)


# class StockOverProcessedTransfer(models.TransientModel):
#     _inherit = "stock.overprocessed.transfer"
#
#     def action_confirm(self):
#         self.ensure_one()
#         if self.picking_id:
#             moves = self.picking_id._get_overprocessed_stock_moves()
#             for move in moves:
#                 if self.picking_id.sale_id:
#                     move_line = self.picking_id.sale_id.order_line.filtered(
#                         lambda l: l.product_id == move.product_id
#                         and l.product_uom_qty == move.product_uom_qty
#                     )
#                     if move_line:
#                         move_line.product_uom_qty = move.quantity_done
#
#         return super().action_confirm()


# class Picking(models.Model):
#     _inherit = "stock.picking"
#
#     def button_validate(self):
#         self.ensure_one()
#
#         print("skip_overprocessed_check :::::::", self._context.get('skip_overprocessed_check'))
#
#         moves = self._get_overprocessed_stock_moves()
#         for move in moves:
#             if self.sale_id:
#
#                 print("self.sale_id :::::::", self.sale_id)
#
#                 move_line = self.sale_id.order_line.filtered(
#                     lambda l: l.product_id == move.product_id
#                     and l.product_uom_qty == move.product_uom_qty
#                 )
#                 if move_line:
#
#                     print("move_line :::::::", move_line)
#
#                     move_line.product_uom_qty = move.quantity_done
#
#             print("move :::::::", move)
#             print("move.product_uom_qty :::::::", move.product_uom_qty)
#             print("move.quantity_done :::::::", move.quantity_done)
#
#             move.product_uom_qty = move.qty_done
#
#         return super().button_validate()

    # def _get_overprocessed_stock_moves(self):
    #     self.ensure_one()
    #     return self.move_lines.filtered(
    #         lambda move: move.product_uom_qty != 0 and float_compare(move.quantity_done, move.product_uom_qty,
    #                                                                  precision_rounding=move.product_uom.rounding) == 1
    #     )


# class StockMoveLine(models.Model):
#     _inherit = "stock.move.line"
#
#     @api.onchange('qty_done')
#     def _onchange_qty_done(self):
#         print("self.qty_done :::::::", self.qty_done)
#         print("self.product_uom_qty :::::::", self.product_uom_qty)
#         if self.qty_done > self.product_uom_qty:
#
#             self.product_uom_qty = self.qty_done
#
#             if self.picking_id:
#                 moves = self.picking_id._get_overprocessed_stock_moves()
#                 for move in moves:
#                     if self.picking_id.sale_id:
#                         move_line = self.picking_id.sale_id.order_line.filtered(
#                             lambda l: l.product_id == move.product_id
#                             and l.product_uom_qty == move.product_uom_qty
#                         )
#                         if move_line:
#                             move_line.product_uom_qty = move.quantity_done


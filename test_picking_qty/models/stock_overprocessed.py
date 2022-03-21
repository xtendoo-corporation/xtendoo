# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Este metodo rellena la referecias a la linea del pedido de la que proviene
# es para corregir un error de Odoo que en los pickings con rutas

from odoo import _, models, api
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = "stock.overprocessed.transfer"

    def action_confirm(self):
        self.ensure_one()
        print("*"*80)
        print("StockOverProcessedTransfer:",self.picking_id.name)
        print("*"*80)

        self.picking_id.action_update_sale_order()

        # picking = self.env["stock.picking"].browse(self.picking_id.id)
        # move_lines = picking.move_line_ids_without_package
        #
        # for line in move_lines:
        #     print("/"*50)
        #     print("qty_done", line.product_qty)
        #     print("product_uom_qty", line.product_uom_qty)
        #     print("/"*50)
        #
        # move_lines = move_lines.filtered(
        #     lambda move: float_compare(move_lines.qty_done, move_lines.product_uom_qty,
        #                                                              precision_rounding=move_lines.move_id.product_uom.rounding) == 1
        # )
        #move_lines = picking.move_line_ids_without_package
        # for line in move_lines:
        #     print("/"*50)
        #     print("qty_done", line.product_qty)
        #     print("product_uom_qty", line.product_uom_qty)
        #     print("/" * 50)
        #
        # print("*"*100)
        # print("entra en action confirm", self.picking_id.id)
        # print("entra en action confirm", move_lines)
        # print("*" * 100)

        return super().action_confirm()



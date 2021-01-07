# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = 'stock.overprocessed.transfer'

    def action_confirm(self):
        self.ensure_one()
        if self.picking_id:
            moves = self.picking_id._get_overprocessed_stock_moves()

            for move in moves:
                print("move overprocessed::::::::::::::", move)
                print("move overprocessed product_id::::::::::::::", move.product_id)
                print("move overprocessed sale order id::::::::::::::", self.picking_id.sale_id)
                print("move overprocessed sale order id::::::::::::::", self.picking_id.sale_id.order_line)

                for line in self.picking_id.sale_id.order_line:
                    print("move overprocessed picking_id.sale_id.order_line::::::::::::::", line)

                if self.picking_id.sale_id:
                    move_line = self.picking_id.sale_id.order_line.filtered(
                        lambda l: l.product_id == move.product_id
                    )
                    if move_line:
                        print("move overprocessed move_line::::::::::::::", move_line)
                        move_line.product_uom_qty = move.quantity_done


        print("================================================")
        print("self.picking_id::::::::::::::", self.picking_id)
        print("self.picking_id.origin::::::::::::::", self.picking_id.origin)
        so = self.env['sale.order'].search([('name', '=', self.picking_id.origin)])
        print("self.sale.order_id::::::::::::::", so)
        print("self.picking_id.move_lines::::::::::::::", self.picking_id.move_lines)

        for line in self.picking_id.move_lines:
            print("line::::::::::::::", line)
            print("line.move_id.sale_line_id::::::::::::::", line.sale_line_id)

        return super().action_confirm()

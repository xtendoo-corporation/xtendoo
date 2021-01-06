# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = 'stock.overprocessed.transfer'

    def action_confirm(self):
        print("self.picking_id::::::::::::::", self.picking_id)
        print("self.picking_id.origin::::::::::::::", self.picking_id.origin)
        so = self.env['sale.order'].search([('name', '=', self.picking_id.origin)])
        print("self.sale.order_id::::::::::::::", so)
        print("self.picking_id.move_lines::::::::::::::", self.picking_id.move_lines)

        for line in self.picking_id.move_lines:
            print("line::::::::::::::", line)
            print("line.move_id.sale_line_id::::::::::::::", line.sale_line_id)

        return super().action_confirm()

# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def get_move_from_line(self, line):
        move = self.env['stock.move']
        # i create this counter to check lot's univocity on move line
        lot_count = 0
        for p in line.order_id.picking_ids:
            for m in p.move_lines:
                move_line_id = m.move_line_ids.filtered(
                    lambda line: line.lot_id)
                if move_line_id and line.lot_id == move_line_id[:1].lot_id:

                    print("*"*80)
                    print(move_line_id)
                    print(line.lot_id)
                    print(move_line_id[:1].lot_id)

                    move = m
                    lot_count += 1
                    # if counter is 0 or > 1 means that something goes wrong
                    if lot_count != 1:
                        raise UserError(_('Can\'t retrieve lot on stock'))
        return move

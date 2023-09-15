# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    return_lot_ids = fields.Many2many(
        'stock.production.lot',
        compute='_get_return_lot'
    )

    def _get_return_lot(self):
        for rec in self:
            returned_move_id = rec.move_id.origin_returned_move_id
            another_returned_move_id = rec.move_id.mapped('move_line_ids').mapped('lot_id')
            if returned_move_id:
                ids = []
                for line in returned_move_id.move_line_ids:
                    ids.append(line.lot_id.id)
                if ids:
                    rec.return_lot_ids = [(4, id) for id in ids]
            elif another_returned_move_id:
                rec.return_lot_ids = [(6, 0, another_returned_move_id.ids)]
            else:
                ids = self.env['stock.production.lot'].search([('product_id', '=', rec.product_id.id)])
                rec.return_lot_ids = [(4, id.id) for id in ids]

# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        val = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        if len(stock_move.move_line_ids) == 1 and stock_move.move_line_ids[:1].lot_id:
            val["lot_id"] = stock_move.move_line_ids[:1].lot_id
        return val

    def _create_returns(self):
        res = super()._create_returns()
        stock_moves = self.env['stock.move']
        stock_move_line = self.env['stock.move.line']
        pick_id = self.env['stock.picking'].browse(res[0])
        for move in pick_id.mapped('move_lines').filtered(
            lambda x: x.state == 'assigned' and x.origin_returned_move_id and x.product_id.tracking == 'lot'):
            if len(move.origin_returned_move_id.move_line_ids) == 1:
                move.move_line_ids.unlink()
                qty = move.product_uom_qty
                line = move.origin_returned_move_id.move_line_ids
                qty_todo = min(qty, line.qty_done)
                vals = move._prepare_move_line_vals(qty_todo)
                val = {'picking_id': vals['picking_id'],
                       'product_id': vals['product_id'],
                       'move_id': move.id,
                       'location_id': vals['location_id'],
                       'location_dest_id': vals['location_dest_id'],
                       'qty_done': qty_todo,
                       'product_uom_id': vals['product_uom_id'],
                       'lot_id': line.lot_id and line.lot_id.id or False,
                       'lot_name': line.lot_id and line.lot_id.name or False}
                stock_move_line.create(val)
            stock_moves |= move
        if stock_moves:
            stock_moves.write({'state': 'assigned'})
        pick_id.action_assign()
        return res


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    lot_id = fields.Many2one(
        comodel_name="stock.production.lot"
    )

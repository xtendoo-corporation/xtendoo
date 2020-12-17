# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        val = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        val["lot_id"] = self.env["stock.return.picking.line"].get_returned_lot_id(stock_move)
        return val

    def _create_returns(self):
        new_picking_id, pick_type_id = super()._create_returns()
        # picking = self.env['stock.picking'].browse(new_picking_id)
        # for line in picking.move_lines:
        #     moves = self.product_return_moves.filtered(lambda l: l.product_id == line.product_id)
        #     if moves:
        #         for move in moves:
        #             if move.lot_id:
        #                 self.env["stock.move.line"].create({
        #                     'picking_id': new_picking_id,
        #                     'location_id': picking.location_id.id,
        #                     'location_dest_id': picking.location_dest_id.id,
        #                     'move_id': line.id,
        #                     'product_id': move.product_id.id,
        #                     'product_uom_id': move.uom_id.id,
        #                     'qty_done': move.quantity,
        #                     'lot_id': move.lot_id.id,
        #                     'product_uom_qty': 0,
        #                 })
        return new_picking_id, pick_type_id


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
    )

    def get_returned_lot_id(self, stock_move):
        if len(stock_move.move_line_ids) == 1 and stock_move.move_line_ids[:1].lot_id:
            return stock_move.move_line_ids[:1].lot_id
        return False


# Copyright 2020 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.tools import float_compare


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        val = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        return val

    def _create_returns(self):
        return super()._create_returns()


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
    )

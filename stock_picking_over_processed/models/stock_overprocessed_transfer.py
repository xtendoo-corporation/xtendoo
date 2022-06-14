# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models, api


class StockOverProcessedTransfer(models.TransientModel):
    _inherit = "stock.overprocessed.transfer"


    def _compute_overprocessed_product_name(self):
        for wizard in self:
            wizard.overprocessed_product_name = False
            if wizard.picking_id:
                moves = wizard.picking_id._get_overprocessed_stock_moves()
                wizard.overprocessed_product_name = "; ".join(moves.mapped("product_id.display_name"))

    def action_confirm(self):
        self.ensure_one()
        self.picking_id.action_update_sale_order()
        return super().action_confirm()



# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Este metodo rellena la referecias a la linea del pedido de la que proviene
# es para corregir un error de Odoo que en los pickings con rutas

from odoo import _, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _action_done(self):
        for line in self.filtered(lambda l: not l.move_id.sale_line_id):
            move_line = line.move_id.picking_id.sale_id.order_line.filtered(
                lambda l: l.product_id == line.product_id
            )
            if move_line:
                line.move_id.sale_line_id = move_line[0]
        super()._action_done()


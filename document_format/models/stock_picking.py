# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Picking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for line in self.move_line_ids:
            if not line.move_id.sale_line_id and line.picking_id.sale_id:
                move_line = line.picking_id.sale_id.order_line.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if move_line:
                    line.move_id.sale_line_id = move_line.id

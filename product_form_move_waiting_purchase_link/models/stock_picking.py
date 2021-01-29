# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class StockPicking(models.Model):
    _inherit = "stock.picking"

    move_product_qty = fields.Float(
        compute="_compute_picking_waiting_product_qty", string="Pickings"
    )

    def _compute_picking_waiting_product_qty(self):
        total_quantity = 0
        self.move_product_qty = 0
        for move_id in self.move_ids_without_package:
            pick_lines = self.env["stock.move.line"].search(
                [
                    ("picking_id", "=", self.id),
                    ("product_id", "=", move_id.product_id.id),
                ]
            )
            if not pick_lines:
                self.move_product_qty = total_quantity
            else:
                for line in pick_lines:
                    delivery_lines = self.env["stock.move"].search(
                        [
                            ("product_id", "=", line.product_id.id),
                            ("state", "not in", ["done", "cancel"]),
                            ("picking_type_id.code", "=", "outgoing"),
                        ]
                    )
                    for delivery_line in delivery_lines:
                        total_quantity = total_quantity + delivery_line.product_uom_qty
                self.move_product_qty = float_round(
                    total_quantity,
                    precision_rounding=pick_lines[0].product_id.uom_id.rounding,
                )

    def action_picking_template_sale_list(self):
        products_ids = self.mapped("move_ids_without_package.product_id").ids
        return {
            "name": _("Detailed Operations"),
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "stock.move",
            "domain": [
                ("product_id", "in", products_ids),
                ("state", "not in", ["done", "cancel"]),
                ("picking_type_id.code", "=", "outgoing"),
            ],
        }

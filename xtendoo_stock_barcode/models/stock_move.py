# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = "stock.move"

    xt_barcode_scanned_qty = fields.Float(
        string="Escaneado PDA",
        digits="Product Unit",
        compute="_compute_xt_barcode_checking",
    )
    xt_barcode_remaining_qty = fields.Float(
        string="Pendiente PDA",
        digits="Product Unit",
        compute="_compute_xt_barcode_checking",
    )
    xt_barcode_check_state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("partial", "Parcial"),
            ("complete", "Completo"),
            ("excess", "Exceso"),
        ],
        string="Estado PDA",
        compute="_compute_xt_barcode_checking",
    )

    @api.depends(
        "product_uom_qty",
        "move_line_ids.quantity",
        "move_line_ids.state",
        "move_line_ids.xt_barcode_product_scanned",
        "state",
        "product_uom.rounding",
    )
    def _compute_xt_barcode_checking(self):
        for move in self:
            rounding = move.product_uom.rounding or move.product_id.uom_id.rounding or 0.01
            demand = move.product_uom_qty
            done = float(
                sum(
                    move.move_line_ids.filtered(
                        lambda line: line.state != "cancel" and line.xt_barcode_product_scanned
                    ).mapped("quantity")
                )
            )
            comparison = float_compare(done, demand, precision_rounding=rounding)
            move.xt_barcode_scanned_qty = done
            move.xt_barcode_remaining_qty = max(demand - done, 0.0)
            if comparison > 0:
                move.xt_barcode_check_state = "excess"
            elif comparison == 0 and (demand or done):
                move.xt_barcode_check_state = "complete"
            elif done:
                move.xt_barcode_check_state = "partial"
            else:
                move.xt_barcode_check_state = "pending"

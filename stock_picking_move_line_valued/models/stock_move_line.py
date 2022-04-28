# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    purchase_line = fields.Many2one(
        related="move_id.purchase_line_id", readonly=True, string="Purchase related order line"
    )
    purchase_tax_id = fields.Many2many(
        related="purchase_line.taxes_id", readonly=True, string="Purchase Tax"
    )
    purchase_price_unit = fields.Float(
        related="purchase_line.price_unit", readonly=True, string="Purchase price unit"
    )
    # purchase_discount = fields.Float(
    #     related="purchase_line.discount", readonly=True, string="Purchase discount (%)"
    # )

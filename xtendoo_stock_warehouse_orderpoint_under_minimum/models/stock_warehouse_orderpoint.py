from odoo import api, fields, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    is_under_minimum = fields.Boolean(
        string="Under Minimum",
        compute="_compute_is_under_minimum",
        store=False,
        help="Indicates if the current quantity on hand is less than the minimum quantity",
    )

    @api.depends("qty_on_hand", "product_min_qty")
    def _compute_is_under_minimum(self):
        """Compute if the current quantity on hand is less than the minimum quantity"""
        for orderpoint in self:
            orderpoint.is_under_minimum = (
                orderpoint.qty_on_hand < orderpoint.product_min_qty
            )

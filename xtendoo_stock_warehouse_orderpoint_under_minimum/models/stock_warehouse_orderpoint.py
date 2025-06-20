from odoo import fields, models, api


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    is_under_minimum = fields.Boolean(
        string="Under Minimum",
        compute="_compute_is_under_minimum",
        store=True,
        help="This field indicates if the current quantity is below the minimum quantity"
    )

    @api.depends("product_min_qty", "qty_on_hand")
    def _compute_is_under_minimum(self):
        for record in self:
            record.is_under_minimum = record.qty_on_hand < record.product_min_qty

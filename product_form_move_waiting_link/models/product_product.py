from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = "product.product"

    move_product_qty = fields.Float(
        compute="_compute_picking_waiting_product_qty", string="Pickings"
    )

    def _compute_picking_waiting_product_qty(self):
        domain = [
            ("state", "not in", ["done", "cancel"]),
            ("product_id", "in", self.ids),
        ]

        pick_type = self.env["stock.picking.type"].search([("code", "=", "outgoing")])
        if pick_type:
            domain.append(("picking_type_id", "=", pick_type[0].id))

        order_lines = self.env["stock.move"].read_group(
            domain, ["product_id", "product_uom_qty"], ["product_id"]
        )
        moved_data = {
            data["product_id"][0]: data["product_uom_qty"] for data in order_lines
        }

        self.move_product_qty = 0
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.move_product_qty = float_round(
                moved_data.get(product.id, 0),
                precision_rounding=product.uom_id.rounding,
            )

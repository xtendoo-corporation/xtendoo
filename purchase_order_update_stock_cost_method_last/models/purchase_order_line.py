from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_update_cost_price(self):
        print("action_update_cost_price :::::")
        for line in self:
            print("product ::::", line.product_id)
            # items.write({"fixed_price": line.price_unit})

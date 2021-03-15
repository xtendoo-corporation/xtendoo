from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_update_cost_price(self):
        print("action_update_cost_price :::::")
        for line in self.filtered(
            lambda l: l.product_id.cost_method == "last"
        ):
            old_standard_price = line.product_id.standard_price
            new_standard_price = line._get_discounted_price_unit()
            line.product_id.write(
                {"standard_price": new_standard_price}
            )
            line.product_id.message_post(
                body=(_("Cost price updated from %s to %s.") % (old_standard_price, new_standard_price))
            )
            # items.write({"fixed_price": line.price_unit})

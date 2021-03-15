from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_update_cost_price(self):
        for line in self.filtered(
            lambda l: l.product_id.cost_method == "last"
        ):
            old_standard_price = line.product_id.standard_price
            new_standard_price = line._get_discounted_price_unit()
            line.product_id.write(
                {"standard_price": new_standard_price}
            )
            line.product_id.message_post(
                body=_("<li>"
                       + "<span>Cost price updated:</span> "
                       + "<span>{} </span>".format(old_standard_price)
                       + "<span class='fa fa-long-arrow-right' role='img' />"
                       + "<span> {}</span>".format(new_standard_price)
                       )
                )

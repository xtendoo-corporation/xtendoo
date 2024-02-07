from collections import defaultdict

from odoo import api, models, fields


class PosOrder(models.Model):
    _inherit = "pos.order"

    loyalty_card_id = fields.Many2one(
        comoodel_name="loyalty.card",
        string="Loyalty Card",
    )

    def add_payment(self, data):
        print("add_payment==================================================")
        print("add_payment", data.get("payment_method_id"))
        print("amount", data.get("amount"))

        payment_method = (self.env["pos.payment.method"].search(
            [("id", "=", data.get("payment_method_id"))]
        ))
        print("payment_method==================================================")
        print("payment_method", payment_method)
        print("payment_method.program_id", payment_method.program_id)
        print("payment_method.used_for_loyalty_program", payment_method.used_for_loyalty_program)

        if (payment_method and payment_method.used_for_loyalty_program and payment_method.program_id
            and data.get("amount") < 0):
            loyalty_card = self.env["loyalty.card"].create(
                {
                    "program_id": payment_method.program_id.id,
                    "points": abs(data.get("amount")),
                    "pos_order_id": data.get("pos_order_id"),
                }
            )
            print("loyalty_card==================================================")
            print("loyalty_card", loyalty_card)

        return super(PosOrder, self).add_payment(data)

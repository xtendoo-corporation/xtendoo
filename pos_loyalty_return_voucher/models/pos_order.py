from datetime import datetime, timedelta

from odoo import api, models, fields


class PosOrder(models.Model):
    _inherit = "pos.order"

    loyalty_card_ids = fields.One2many(
        comodel_name="loyalty.card",
        inverse_name="pos_order_id",
        string="Loyalty Card",
    )
    loyalty_card_code = fields.Char(
        string="Loyalty Card",
        compute="_compute_loyalty_card",
    )
    loyalty_card_expiration_date = fields.Date(
        string="Loyalty Card Expire",
        compute="_compute_loyalty_card",
    )

    @api.depends('loyalty_card_ids')
    def _compute_loyalty_card(self):
        for order in self:
            if order.loyalty_card_ids:
                order.loyalty_card_code = order.loyalty_card_ids[-1].code
                order.loyalty_card_expiration_date = order.loyalty_card_ids[-1].expiration_date
            else:
                order.loyalty_card_code = ""
                order.loyalty_card_expiration_date = ""

    @api.model
    def get_loyalty_card_code_from_order(self, order_ids):
        order = self.env["pos.order"].browse(order_ids)
        if order:
            return {
                'code': order.loyalty_card_code,
                'expiration_date': order.loyalty_card_expiration_date,
                }

    # @api.model
    # def _order_fields(self, ui_order):
    #     order_fields = super(PosOrder, self)._order_fields(ui_order)
    #     order_fields['loyalty_card_code'] = ui_order.get('loyalty_card_code')
    #     return order_fields
    #
    # def _export_for_ui(self, order):
    #     result = super(PosOrder, self)._export_for_ui(order)
    #     result.update({
    #         'loyalty_card_code': order.loyalty_card_code,
    #     })
    #     return result

    def add_payment(self, data):
        payment_method = self.env["pos.payment.method"].search(
            [
                ("id", "=", data.get("payment_method_id")),
                ("used_for_loyalty_program", "=", True),
                ("program_id", "!=", False)
            ]
        )
        if payment_method and data.get("amount") < 0:
            loyalty_card = {
                "program_id": payment_method.program_id.id,
                "points": abs(data.get("amount")),
                "pos_order_id": data.get("pos_order_id"),
            }
            validity = int(self.env['ir.config_parameter'].sudo().get_param(
                'pos_loyalty_return_voucher.return_voucher_validity', default=0
            ))
            if validity > 0:
                loyalty_card.update(
                    {"expiration_date": datetime.now() + timedelta(days=validity)}
                )
            self.env["loyalty.card"].create(loyalty_card)
        return super(PosOrder, self).add_payment(data)

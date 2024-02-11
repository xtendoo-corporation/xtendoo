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
        compute="_compute_loyalty_card_code",
    )

    @api.depends('loyalty_card_ids')
    def _compute_loyalty_card_code(self):
        for order in self:
            if order.loyalty_card_ids:
                order.loyalty_card_code = order.loyalty_card_ids[-1].code
            else:
                order.loyalty_card_code = ""

            print("*" * 80)
            print("order.loyalty_card", order.loyalty_card_code)

    @api.model
    def _process_order(self, pos_order, draft, existing_order):
        pos_order["data"].update(
            {"loyalty_card_code": "999"}
        )
        return super()._process_order(pos_order, draft, existing_order)

    @api.model
    def get_loyalty_card_code_from_order(self, order_ids):
        print("get_loyalty_card_code_from_order==================================================")
        print("order_ids", order_ids)
        loyalty_card_codes = (
            self.env["pos.order"].browse(order_ids).mapped("loyalty_card_code")
        )
        print("loyalty_card_codes", loyalty_card_codes)
        return {"code": loyalty_card_codes}

    @api.model
    def _order_fields(self, ui_order):
        print("/" * 80)
        print("ui_order", ui_order)
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['loyalty_card_code'] = ui_order.get('loyalty_card_code')
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'loyalty_card_code': order.loyalty_card_code,
        })
        return result

    def add_payment(self, data):
        print("add_payment==================================================")
        print("data", data)
        print("add_payment", data.get("payment_method_id"))
        print("amount", data.get("amount"))

        payment_method = self.env["pos.payment.method"].search(
            [
                ("id", "=", data.get("payment_method_id")),
                ("used_for_loyalty_program", "=", True),
                ("program_id", "!=", False)
            ]
        )
        print("payment_method==================================================")
        print("payment_method", payment_method)
        print("payment_method.program_id", payment_method.program_id)
        print("payment_method.used_for_loyalty_program", payment_method.used_for_loyalty_program)
        # print("self.return_voucher_validity", self.env.company.return_voucher_validity)

        # // obtain the return_voucher_validity from the res.config.settings

        if payment_method and data.get("amount") < 0:
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


{'name': 'Order 00024-098-0006', 'amount_paid': 120.5, 'amount_total': 120.5, 'amount_tax': 0, 'amount_return': 0,
 'lines': [[0, 0, {'qty': 1, 'price_unit': 120.5, 'price_subtotal': 120.5, 'price_subtotal_incl': 120.5, 'discount': 0,
                   'product_id': 25, 'tax_ids': [[6, False, []]], 'id': 231, 'pack_lot_ids': [], 'description': '',
                   'full_product_name': 'Office Chair Black', 'price_extra': 0, 'customer_note': '',
                   'price_manually_set': False, 'price_automatically_set': False, 'eWalletGiftCardProgramId': None}]],
 'statement_ids': [[0, 0, {'name': '2024-02-10 00:57:30', 'payment_method_id': 1, 'amount': 120.5, 'payment_status': '',
                           'ticket': '', 'card_type': '', 'cardholder_name': '', 'transaction_id': '',
                           'coupon_data': None}]], 'pos_session_id': 24, 'pricelist_id': 1, 'partner_id': False,
 'user_id': 2, 'uid': '00024-098-0006', 'sequence_number': 6, 'creation_date': '2024-02-10T00:57:30.775Z',
 'fiscal_position_id': False, 'server_id': False, 'to_invoice': False, 'to_ship': False, 'is_tipped': False,
 'tip_amount': 0, 'access_token': '4ad35b15-13c4-4f1b-b1a7-d61f88ebd5c2', 'disabledRewards': [],
 'codeActivatedProgramRules': [], 'codeActivatedCoupons': [],
 'couponPointChanges': {'-2': {'points': 1, 'program_id': 5, 'coupon_id': -2, 'appliedRules': [5]}}}

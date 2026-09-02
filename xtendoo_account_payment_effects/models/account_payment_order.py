from odoo import fields, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    xtd_source_type = fields.Selection(
        selection=[
            ("oca", "Pending Transactions"),
            ("existing_payments", "Existing Payments"),
        ],
        string="Source Type",
        default="oca",
        required=True,
        copy=False,
        tracking=True,
    )

    def _xtd_existing_payments_orders(self):
        return self.filtered(lambda order: order.xtd_source_type == "existing_payments")

    def xtd_create_from_existing_payments(self, payments, lot_date):
        self.ensure_one()
        payments._xtd_validate_for_effect_lot()
        if self.xtd_source_type != "existing_payments":
            raise UserError(
                self.env._(
                    "This payment/debit order is not configured for existing payments."
                )
            )
        if self.state != "draft":
            raise UserError(
                self.env._(
                    "Only draft payment/debit orders can receive existing payments."
                )
            )
        if self.payment_ids or self.payment_lot_ids:
            raise UserError(
                self.env._(
                    "This payment/debit order already contains payments or lots."
                )
            )
        lot = self.env["account.payment.lot"].create(
            {
                "order_id": self.id,
                "currency_id": payments[0].currency_id.id,
                "date": lot_date,
                "name": f"{self.name}/LOT1",
            }
        )
        payments.write(
            {
                "payment_order_id": self.id,
                "payment_lot_id": lot.id,
            }
        )
        self.write(
            {
                "state": "uploaded",
                "date_generated": False,
                "date_uploaded": lot_date,
            }
        )
        return lot

    def cancel2draft(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).cancel2draft() if regular_orders else True
        for order in xtd_orders:
            if order.payment_ids.filtered("is_matched"):
                raise UserError(
                    self.env._(
                        "You cannot reset this lot because it contains payments already "
                        "matched with bank transactions."
                    )
                )
            if order.payment_file_id:
                order.payment_file_id.unlink()
            order.payment_ids.write(
                {
                    "payment_lot_id": False,
                    "payment_order_id": False,
                }
            )
            order.payment_lot_ids.unlink()
            order.write(
                {
                    "state": "draft",
                    "date_generated": False,
                    "date_uploaded": False,
                    "payment_file_id": False,
                }
            )
        return result

    def action_cancel(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).action_cancel() if regular_orders else True
        for order in xtd_orders:
            if order.payment_ids.filtered("is_matched"):
                raise UserError(
                    self.env._(
                        "You cannot cancel this lot because it contains payments already "
                        "matched with bank transactions."
                    )
                )
            if order.payment_file_id:
                order.payment_file_id.unlink()
            order.payment_ids.write(
                {
                    "payment_lot_id": False,
                    "payment_order_id": False,
                }
            )
            order.payment_lot_ids.unlink()
            order.write(
                {
                    "state": "cancel",
                    "date_generated": False,
                    "payment_file_id": False,
                }
            )
        return result

    def draft2open(self):
        xtd_orders = self._xtd_existing_payments_orders()
        if xtd_orders:
            raise UserError(
                self.env._(
                    "Orders created from existing payments must be generated from the "
                    "deposit/remittance wizard."
                )
            )
        return super().draft2open()

    def open2generated(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).open2generated() if regular_orders else {}
        if xtd_orders:
            raise UserError(
                self.env._(
                    "File generation is not available for payment/debit orders built "
                    "from existing payments."
                )
            )
        return result

    def generated2uploaded(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).generated2uploaded() if regular_orders else True
        for order in xtd_orders:
            order.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(order),
                }
            )
        return result


from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


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
    xtd_manage_effects_method = fields.Boolean(
        related="payment_method_line_id.xtd_manage_effects"
    )
    xtd_bank_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario de banco",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        check_company=True,
        copy=False,
        help="Diario de destino de la remesa. Puede ser distinto del diario "
        "asociado al método de pago.",
    )
    xtd_existing_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        relation="xtd_account_payment_order_existing_payment_rel",
        column1="order_id",
        column2="payment_id",
        string="Pagos existentes a incluir",
        copy=False,
    )
    xtd_deposit_date = fields.Date(
        string="Fecha de depósito/remesa",
        default=fields.Date.context_today,
        copy=False,
    )

    @api.onchange("payment_method_line_id")
    def _onchange_payment_method_line_id_xtd_bank_journal(self):
        if self.payment_method_line_id and not self.xtd_bank_journal_id:
            self.xtd_bank_journal_id = self.payment_method_line_id.journal_id

    def _xtd_eligible_existing_payments_domain(self):
        self.ensure_one()
        journal = self.xtd_bank_journal_id or self.journal_id
        return [
            ("payment_type", "=", "inbound"),
            ("partner_type", "=", "customer"),
            ("payment_lot_id", "=", False),
            ("payment_order_id", "=", False),
            ("is_matched", "=", False),
            ("state", "not in", ("draft", "canceled", "rejected")),
            ("company_id", "=", self.company_id.id),
            ("journal_id", "=", journal.id),
            ("payment_method_line_id.xtd_manage_effects", "=", True),
        ]

    def xtd_action_import_existing_payments(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                self.env._(
                    "Only draft payment/debit orders can import existing payments."
                )
            )
        if self.payment_ids or self.payment_lot_ids:
            raise UserError(
                self.env._(
                    "This payment/debit order already contains payments or lots."
                )
            )
        if not self.xtd_bank_journal_id:
            raise UserError(
                self.env._("Select a destination bank journal before importing.")
            )
        eligible_payments = self.env["account.payment"].search(
            self._xtd_eligible_existing_payments_domain()
        )
        self.write(
            {
                "xtd_source_type": "existing_payments",
                "journal_id": self.xtd_bank_journal_id.id,
                "xtd_existing_payment_ids": [Command.set(eligible_payments.ids)],
                "xtd_deposit_date": (
                    self.xtd_deposit_date or fields.Date.context_today(self)
                ),
            }
        )
        return True

    def xtd_action_confirm_existing_payments(self):
        self.ensure_one()
        if not self.xtd_existing_payment_ids:
            raise UserError(
                self.env._(
                    "Select at least one existing payment to include in the lot."
                )
            )
        lot = self.xtd_create_from_existing_payments(
            self.xtd_existing_payment_ids,
            self.xtd_deposit_date or fields.Date.context_today(self),
        )
        self.xtd_existing_payment_ids = [Command.clear()]
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.lot",
            "views": [(False, "form")],
            "res_id": lot.id,
            "target": "current",
            "context": {"account_payment_lot_main_view": True},
        }

    def _xtd_existing_payments_orders(self):
        return self.filtered(lambda order: order.xtd_source_type == "existing_payments")

    def xtd_create_from_existing_payments(self, payments, lot_date):
        self.ensure_one()
        payments._xtd_validate_for_effect_lot()
        if len(payments.journal_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments with different journals in the "
                    "same lot."
                )
            )
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
                    "Orders created from existing payments must be confirmed with "
                    "the 'Confirmar pagos' button in the 'Pagos existentes' tab."
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


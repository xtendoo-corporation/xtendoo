from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    xtd_manage_effects = fields.Boolean(
        related="payment_method_line_id.xtd_manage_effects"
    )
    xtd_effect_reference_required = fields.Boolean(
        related="payment_method_line_id.xtd_effect_reference_required"
    )
    xtd_effect_due_date_required = fields.Boolean(
        related="payment_method_line_id.xtd_effect_due_date_required"
    )
    xtd_effect_due_date = fields.Date(string="Effect Due Date", tracking=True)
    xtd_effect_status = fields.Selection(
        selection=[
            ("portfolio", "In Portfolio"),
            ("deposited", "Deposited"),
            ("collected", "Collected"),
            ("rejected", "Rejected"),
            ("canceled", "Canceled"),
        ],
        compute="_compute_xtd_effect_status",
        string="Effect Status",
    )

    @api.depends("xtd_manage_effects", "payment_lot_id", "is_matched", "state")
    def _compute_xtd_effect_status(self):
        for payment in self:
            status = False
            if payment.xtd_manage_effects:
                if payment.state == "rejected":
                    status = "rejected"
                elif payment.state == "canceled":
                    status = "canceled"
                elif payment.is_matched:
                    status = "collected"
                elif payment.payment_lot_id:
                    status = "deposited"
                else:
                    status = "portfolio"
            payment.xtd_effect_status = status

    @api.constrains("payment_reference", "xtd_effect_due_date")
    def _check_xtd_effect_fields(self):
        for payment in self.filtered("xtd_manage_effects"):
            if (
                payment.xtd_effect_reference_required
                and not payment.payment_reference
            ):
                raise ValidationError(
                    self.env._(
                        "You must set the effect reference/number for the payment "
                        "method '%s'.",
                        payment.payment_method_line_id.display_name,
                    )
                )
            if payment.xtd_effect_due_date_required and not payment.xtd_effect_due_date:
                raise ValidationError(
                    self.env._("You must set the effect due date.")
                )

    def _xtd_validate_effect_payment_data(self):
        for payment in self:
            if not payment.xtd_manage_effects:
                continue
            if (
                payment.xtd_effect_reference_required
                and not payment.payment_reference
            ):
                raise UserError(
                    self.env._(
                        "You must set the effect reference/number for the payment "
                        "method '%s'.",
                        payment.payment_method_line_id.display_name,
                    )
                )
            if payment.xtd_effect_due_date_required and not payment.xtd_effect_due_date:
                raise UserError(self.env._("You must set the effect due date."))

    def _xtd_validate_for_effect_lot(self):
        if not self:
            raise UserError(self.env._("You must select at least one payment."))
        wrong_payment_type = self.filtered(lambda pay: pay.payment_type != "inbound")
        if wrong_payment_type:
            raise UserError(
                self.env._("Only inbound payments can be included in a collection lot.")
            )
        wrong_partner_type = self.filtered(lambda pay: pay.partner_type != "customer")
        if wrong_partner_type:
            raise UserError(
                self.env._("Only customer payments can be included in a collection lot.")
            )
        unmanaged = self.filtered(lambda pay: not pay.xtd_manage_effects)
        if unmanaged:
            raise UserError(
                self.env._(
                    "All selected payments must use a payment method configured as a "
                    "collection effect."
                )
            )
        invalid_state = self.filtered(lambda pay: pay.state in ("draft", "canceled", "rejected"))
        if invalid_state:
            raise UserError(
                self.env._(
                    "Draft, canceled or rejected payments cannot be included in a "
                    "collection lot."
                )
            )
        matched = self.filtered("is_matched")
        if matched:
            raise UserError(
                self.env._(
                    "Matched payments cannot be included in a collection lot."
                )
            )
        already_in_lot = self.filtered("payment_lot_id")
        if already_in_lot:
            raise UserError(
                self.env._("You cannot include a payment that is already assigned to a lot.")
            )
        already_in_order = self.filtered("payment_order_id")
        if already_in_order:
            raise UserError(
                self.env._(
                    "You cannot include a payment that is already assigned to a "
                    "payment/debit order."
                )
            )
        if len(self.company_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments from different companies in the same lot."
                )
            )
        if len(self.currency_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments with different currencies in the same lot."
                )
            )
        non_positive = self.filtered(lambda pay: pay.amount <= 0)
        if non_positive:
            raise UserError(
                self.env._("You can only include payments with a strictly positive amount.")
            )
        self._xtd_validate_effect_payment_data()
        if len(self.journal_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments with different journals in the same lot."
                )
            )
        if len(self.payment_method_line_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments with different collection methods in the same lot."
                )
            )
        return True

    def _xtd_get_effect_lot_vals(self):
        self._xtd_validate_for_effect_lot()
        payments = self.sorted(key=lambda pay: (pay.date or fields.Date.today(), pay.id))
        return {
            "company_id": payments[0].company_id.id,
            "currency_id": payments[0].currency_id.id,
            "journal_id": payments[0].journal_id.id,
            "payment_method_line_id": payments[0].payment_method_line_id.id,
            "payment_count": len(payments),
            "amount_total": sum(payments.mapped("amount")),
        }




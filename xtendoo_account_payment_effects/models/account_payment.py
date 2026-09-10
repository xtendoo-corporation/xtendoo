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
    xtd_remesa_id = fields.Many2one(
        comodel_name="account.payment.remesa",
        string="Remesa",
        copy=False,
        tracking=True,
    )
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

    @api.depends("xtd_manage_effects", "xtd_remesa_id", "xtd_remesa_id.state", "is_matched", "state")
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
                elif payment.xtd_remesa_id:
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

    def _xtd_validate_for_remesa(self):
        if not self:
            raise UserError(self.env._("You must select at least one payment."))
        wrong_payment_type = self.filtered(lambda pay: pay.payment_type != "inbound")
        if wrong_payment_type:
            raise UserError(
                self.env._("Only inbound payments can be included in a remesa.")
            )
        wrong_partner_type = self.filtered(lambda pay: pay.partner_type != "customer")
        if wrong_partner_type:
            raise UserError(
                self.env._("Only customer payments can be included in a remesa.")
            )
        unmanaged = self.filtered(lambda pay: not pay.xtd_manage_effects)
        if unmanaged:
            raise UserError(
                self.env._(
                    "All selected payments must use a payment method configured as a "
                    "collection effect."
                )
            )
        invalid_state = self.filtered(lambda pay: pay.state in ("canceled", "rejected"))
        if invalid_state:
            raise UserError(
                self.env._(
                    "Canceled or rejected payments cannot be included in a remesa."
                )
            )
        matched = self.filtered("is_matched")
        if matched:
            raise UserError(
                self.env._("Matched payments cannot be included in a remesa.")
            )
        already_in_remesa = self.filtered(
            lambda pay: pay.xtd_remesa_id and pay.xtd_remesa_id not in self.xtd_remesa_id
        )
        if already_in_remesa:
            raise UserError(
                self.env._("You cannot include a payment that is already assigned to "
                            "another remesa.")
            )
        if len(self.company_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments from different companies in the same "
                    "remesa."
                )
            )
        if len(self.currency_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot include payments with different currencies in the same "
                    "remesa."
                )
            )
        non_positive = self.filtered(lambda pay: pay.amount <= 0)
        if non_positive:
            raise UserError(
                self.env._("You can only include payments with a strictly positive amount.")
            )
        self._xtd_validate_effect_payment_data()
        return True

    def _xtd_check_not_matched_for_destructive_action(self):
        matched_effects = self.filtered(
            lambda pay: pay.xtd_manage_effects and pay.is_matched
        )
        if matched_effects:
            raise UserError(
                self.env._(
                    "You cannot reject or cancel a collection effect that is "
                    "already matched with a bank transaction. Reverse the bank "
                    "matching first with an offsetting bank statement line and "
                    "reconcile it, then reject or cancel the payment."
                )
            )

    def action_reject(self):
        self._xtd_check_not_matched_for_destructive_action()
        return super().action_reject()

    def action_cancel(self):
        self._xtd_check_not_matched_for_destructive_action()
        return super().action_cancel()

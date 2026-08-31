from odoo import fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    xtd_manage_effects = fields.Boolean(
        related="payment_method_line_id.xtd_manage_effects"
    )
    xtd_effect_reference_required = fields.Boolean(
        related="payment_method_line_id.xtd_effect_reference_required"
    )
    xtd_effect_due_date_required = fields.Boolean(
        related="payment_method_line_id.xtd_effect_due_date_required"
    )
    xtd_payment_reference = fields.Char(string="Effect Reference")
    xtd_effect_due_date = fields.Date(string="Effect Due Date")

    def _xtd_validate_effect_fields(self):
        self.ensure_one()
        if not self.xtd_manage_effects:
            return
        if self.xtd_effect_reference_required and not self.xtd_payment_reference:
            raise UserError(
                self.env._(
                    "You must set the effect reference/number for the payment "
                    "method '%s'.",
                    self.payment_method_line_id.display_name,
                )
            )
        if self.xtd_effect_due_date_required and not self.xtd_effect_due_date:
            raise UserError(self.env._("You must set the effect due date."))

    def _xtd_prepare_effect_payment_vals(self):
        self.ensure_one()
        if not self.xtd_manage_effects:
            return {}
        self._xtd_validate_effect_fields()
        return {
            "payment_reference": self.xtd_payment_reference,
            "xtd_effect_due_date": self.xtd_effect_due_date,
        }

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals.update(self._xtd_prepare_effect_payment_vals())
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals.update(self._xtd_prepare_effect_payment_vals())
        return payment_vals


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    xtd_manage_effects = fields.Boolean(
        string="Manage as Collection Effect",
        help="Use this payment method line to manage customer collection effects "
        "such as checks, promissory notes or similar instruments.",
    )
    xtd_effect_reference_required = fields.Boolean(
        string="Effect Reference Required",
        help="Require a reference/number when registering a payment with this "
        "payment method line.",
    )
    xtd_effect_due_date_required = fields.Boolean(
        string="Effect Due Date Required",
        help="Require an effect due date when registering a payment with this "
        "payment method line.",
    )

    @api.constrains("xtd_manage_effects", "payment_method_id", "payment_account_id")
    def _check_xtd_manage_effects_configuration(self):
        for line in self.filtered("xtd_manage_effects"):
            if line.payment_type != "inbound":
                raise ValidationError(
                    self.env._(
                        "Payment method '%(method)s' can only manage collection "
                        "effects when its payment type is Inbound.",
                        method=line.display_name,
                    )
                )
            if not line.payment_account_id:
                raise ValidationError(
                    self.env._(
                        "Payment method '%(method)s' must define an outstanding "
                        "receipt account to manage collection effects.",
                        method=line.display_name,
                    )
                )
            if not line.payment_account_id.reconcile:
                raise ValidationError(
                    self.env._(
                        "The outstanding receipt account of '%(method)s' "
                        "('%(account)s') must be reconcilable, otherwise payments "
                        "flip to 'Paid' immediately and never wait for the remesa "
                        "to be confirmed.",
                        method=line.display_name,
                        account=line.payment_account_id.display_name,
                    )
                )

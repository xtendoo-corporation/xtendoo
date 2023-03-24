import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Inherit to implement the tax calculation using avatax API"""

    _inherit = "account.move"

    @api.depends(
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "avatax_amount",
    )
    def _compute_amount(self):
        res = super()._compute_amount()
        for move in self:
            if move._payment_state_matters() and move.state == 'posted':
                reconciled_payments = move._get_reconciled_payments()
                for reconciled_payment in reconciled_payments:
                    print("*"*80)
                    print("reconciled_payment", reconciled_payment)
                    print("*"*80)
        return res


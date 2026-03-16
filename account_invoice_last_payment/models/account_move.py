# Copyright 2023 Camilo <Xtendoo, https://xtendoo.es/>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveCustom(models.Model):
    _inherit = "account.move"

    last_payment = fields.Date(string="Last payment")

    def _get_last_payment_date(self):
        self.ensure_one()
        if self.state != "posted" or not self.is_invoice(include_receipts=True):
            return False

        reconciled_payments = self._get_reconciled_payments().sorted(
            key=lambda payment: payment.date,
            reverse=True,
        )
        return reconciled_payments[0].date if reconciled_payments else False

    @api.depends(
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
    )
    def _compute_amount(self):
        res = super()._compute_amount()
        for move in self:
            move.last_payment = move._get_last_payment_date()
        return res

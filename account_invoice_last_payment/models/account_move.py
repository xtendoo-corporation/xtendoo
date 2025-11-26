# Copyright 2023 Camilo <Xtendoo, https://xtendoo.es/>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveCustom(models.Model):
    """Inherit to implement the tax calculation using avatax API"""

    _inherit = "account.move"

    last_payment = fields.Date(string="Last payment")

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
            if move._payment_state_matters() and move.state == 'posted':
                reconciled_payments = move._get_reconciled_payments().sorted(key=lambda x: x.date, reverse=True)
                if reconciled_payments:
                    move.last_payment = reconciled_payments[0].date
        return res

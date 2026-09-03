from odoo import api, fields, models


class AccountPaymentLot(models.Model):
    _inherit = "account.payment.lot"

    xtd_source_type = fields.Selection(related="order_id.xtd_source_type")
    xtd_is_matched = fields.Boolean(
        string="Fully Matched",
        compute="_compute_xtd_is_matched",
        store=True,
    )

    @api.depends("payment_ids", "payment_ids.is_matched")
    def _compute_xtd_is_matched(self):
        for lot in self:
            lot.xtd_is_matched = bool(lot.payment_ids) and all(
                payment.is_matched for payment in lot.payment_ids
            )

    def _get_move_lines_to_reconcile(self):
        move_lines = self.env["account.move.line"]
        for lot in self:
            payments = lot.payment_ids.filtered(
                lambda payment: payment.move_id
                and payment.state not in ("draft", "canceled", "rejected")
                and not payment.is_matched
            )
            for payment in payments:
                liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
                move_lines |= liquidity_lines.filtered(
                    lambda line: line.account_id.reconcile and not line.reconciled
                )
        return move_lines


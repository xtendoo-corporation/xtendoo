from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    xtd_payment_lot_id = fields.Many2one(
        comodel_name="account.payment.lot",
        string="Payment Lot",
        store=False,
        check_company=True,
        domain="[(\"payment_type\", \"=\", \"inbound\"), (\"company_id\", \"=\", company_id), (\"journal_id\", \"=\", journal_id), (\"xtd_is_matched\", \"=\", False)]",
    )

    @api.onchange("xtd_payment_lot_id")
    def _onchange_xtd_payment_lot_id(self):
        for line in self.filtered("xtd_payment_lot_id"):
            line.xtd_add_payment_lot(line.xtd_payment_lot_id)
            line.xtd_payment_lot_id = False

    def xtd_add_payment_lot(self, payment_lot):
        self.ensure_one()
        move_lines = payment_lot._get_move_lines_to_reconcile()
        if not move_lines:
            raise UserError(
                self.env._(
                    "The selected payment lot has no pending move lines to reconcile."
                )
            )
        for move_line in move_lines:
            self._add_account_move_line(move_line)
        return True


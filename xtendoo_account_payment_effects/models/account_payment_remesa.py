from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRemesa(models.Model):
    _name = "account.payment.remesa"
    _description = "Customer Collection Effects Remittance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env._("New"),
    )
    date = fields.Date(
        string="Fecha de remesa",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario de banco",
        required=True,
        check_company=True,
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        help="Diario en el que se registrará el depósito de la remesa.",
    )
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Método de pago",
        required=True,
        check_company=True,
        domain="[('xtd_manage_effects', '=', True), ('payment_type', '=', 'inbound'),"
        " ('company_id', '=', company_id)]",
    )
    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="xtd_remesa_id",
        string="Pagos",
        domain="[('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer'),"
        " ('payment_method_line_id', '=', payment_method_line_id),"
        " ('xtd_remesa_id', '=', False), ('is_matched', '=', False),"
        " ('state', 'not in', ('draft', 'canceled', 'rejected')),"
        " ('company_id', '=', company_id)]",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
    )
    payment_count = fields.Integer(compute="_compute_totals")
    amount_total = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    state = fields.Selection(
        selection=[("draft", "Borrador"), ("confirmed", "Confirmada")],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    statement_line_id = fields.Many2one(
        comodel_name="account.bank.statement.line",
        string="Apunte de banco",
        readonly=True,
        copy=False,
    )

    @api.depends("journal_id", "company_id")
    def _compute_currency_id(self):
        for remesa in self:
            remesa.currency_id = (
                remesa.journal_id.currency_id
                or remesa.company_id.currency_id
                or self.env.company.currency_id
            )

    @api.depends("payment_ids", "payment_ids.amount")
    def _compute_totals(self):
        for remesa in self:
            remesa.payment_count = len(remesa.payment_ids)
            remesa.amount_total = sum(remesa.payment_ids.mapped("amount"))

    @api.constrains("payment_ids", "payment_method_line_id", "company_id", "currency_id")
    def _check_payments_consistency(self):
        for remesa in self:
            payments = remesa.payment_ids
            if not payments:
                continue
            if any(payment.company_id != remesa.company_id for payment in payments):
                raise UserError(
                    self.env._("All payments in a remesa must belong to the same company.")
                )
            if len(payments.currency_id) > 1 or (
                payments.currency_id and payments.currency_id != remesa.currency_id
            ):
                raise UserError(
                    self.env._("All payments in a remesa must share the same currency.")
                )
            wrong_method = payments.filtered(
                lambda pay: pay.payment_method_line_id != remesa.payment_method_line_id
            )
            if wrong_method:
                raise UserError(
                    self.env._(
                        "All payments in a remesa must use the same payment method "
                        "as the remesa."
                    )
                )
            already_used = payments.filtered(
                lambda pay: pay.xtd_remesa_id and pay.xtd_remesa_id != remesa
            )
            if already_used:
                raise UserError(
                    self.env._(
                        "You cannot include a payment that is already assigned to "
                        "another remesa."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == self.env._("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.payment.remesa"
                ) or self.env._("New")
        return super().create(vals_list)

    def _xtd_eligible_payments_domain(self):
        self.ensure_one()
        return [
            ("payment_type", "=", "inbound"),
            ("partner_type", "=", "customer"),
            ("payment_method_line_id", "=", self.payment_method_line_id.id),
            ("xtd_remesa_id", "=", False),
            ("is_matched", "=", False),
            ("state", "not in", ("draft", "canceled", "rejected")),
            ("company_id", "=", self.company_id.id),
        ]

    def action_fetch_eligible_payments(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Only draft remesas can fetch payments."))
        if not self.payment_method_line_id:
            raise UserError(
                self.env._("Select a payment method before fetching payments.")
            )
        new_payments = self.env["account.payment"].search(
            self._xtd_eligible_payments_domain()
        )
        if not new_payments:
            raise UserError(
                self.env._(
                    "No pending payments found for this payment method and company."
                )
            )
        self.payment_ids = [Command.link(payment.id) for payment in new_payments]
        return True

    def action_confirm(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Only draft remesas can be confirmed."))
        if not self.payment_ids:
            raise UserError(
                self.env._("Add at least one payment to the remesa before confirming.")
            )
        payments = self.payment_ids
        payments._xtd_validate_for_remesa()

        draft_payments = payments.filtered(lambda pay: pay.state == "draft")
        if draft_payments:
            draft_payments.action_post()

        outstanding_account = self.payment_method_line_id.payment_account_id
        if not outstanding_account:
            raise UserError(
                self.env._(
                    "The payment method '%s' has no outstanding account configured.",
                    self.payment_method_line_id.display_name,
                )
            )

        outstanding_lines = self.env["account.move.line"]
        for payment in payments:
            liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
            outstanding_lines |= liquidity_lines.filtered(
                lambda line: line.account_id == outstanding_account and not line.reconciled
            )

        if not outstanding_lines:
            raise UserError(
                self.env._("No pending outstanding move lines found for these payments.")
            )

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal_id.id,
                "date": self.date,
                "payment_ref": self.name,
                "amount": self.amount_total,
                "counterpart_account_id": outstanding_account.id,
            }
        )
        counterpart_line = statement_line.move_id.line_ids.filtered(
            lambda line: line.account_id == outstanding_account
        )
        (outstanding_lines + counterpart_line).reconcile()

        self.write({"state": "confirmed", "statement_line_id": statement_line.id})
        return True

    def action_draft(self):
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(self.env._("Only confirmed remesas can be reset to draft."))
        statement_line = self.statement_line_id
        if statement_line:
            statement_line.move_id.line_ids.remove_move_reconcile()
            statement_line.unlink()
        self.write({"state": "draft", "statement_line_id": False})
        return True

from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools.misc import format_date


class XtdCreatePaymentLotWizard(models.TransientModel):
    _name = "xtd.account.payment.lot.create.wizard"
    _description = "Create Payment Lot From Existing Payments"

    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="Selected Payments",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Bank Journal",
        required=True,
        readonly=True,
        check_company=True,
    )
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Payment Method",
        required=True,
        readonly=True,
        check_company=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        readonly=True,
    )
    date = fields.Date(
        string="Deposit/Remittance Date",
        required=True,
        default=fields.Date.context_today,
    )
    description = fields.Char(string="Description")
    payment_count = fields.Integer(compute="_compute_totals", string="Effects")
    amount_total = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Total",
    )

    @api.depends("payment_ids", "payment_ids.amount")
    def _compute_totals(self):
        for wizard in self:
            wizard.payment_count = len(wizard.payment_ids)
            wizard.amount_total = sum(list(wizard.payment_ids.mapped("amount")))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") != "account.payment":
            return res
        payments = self.env["account.payment"].browse(
            self.env.context.get("active_ids", [])
        ).exists()
        vals = payments._xtd_get_effect_lot_vals()
        default_date = res.get("date") or fields.Date.context_today(self)
        res.update(
            {
                "payment_ids": [Command.set(payments.ids)],
                "company_id": vals["company_id"],
                "journal_id": vals["journal_id"],
                "payment_method_line_id": vals["payment_method_line_id"],
                "currency_id": vals["currency_id"],
                "description": self.env._(
                    "Deposit/Remittance %s", format_date(self.env, default_date)
                ),
            }
        )
        return res

    def action_create_lot(self):
        self.ensure_one()
        self.payment_ids._xtd_validate_for_effect_lot()
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.payment_method_line_id.id,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
                "date_prefered": "fixed",
                "date_scheduled": self.date,
                "description": self.description,
                "xtd_source_type": "existing_payments",
            }
        )
        lot = order.xtd_create_from_existing_payments(self.payment_ids, self.date)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.lot",
            "views": [(False, "form")],
            "res_id": lot.id,
            "target": "current",
            "context": {"account_payment_lot_main_view": True},
        }



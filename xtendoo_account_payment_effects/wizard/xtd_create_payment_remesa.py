from odoo import api, fields, models
from odoo.fields import Command


class XtdCreatePaymentRemesaWizard(models.TransientModel):
    _name = "xtd.account.payment.remesa.create.wizard"
    _description = "Create Remesa From Existing Payments"

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
        string="Fecha de remesa",
        required=True,
        default=fields.Date.context_today,
    )
    payment_count = fields.Integer(compute="_compute_totals", string="Efectos")
    amount_total = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        string="Total",
    )

    @api.depends("payment_ids", "payment_ids.amount")
    def _compute_totals(self):
        for wizard in self:
            wizard.payment_count = len(wizard.payment_ids)
            wizard.amount_total = sum(wizard.payment_ids.mapped("amount"))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") != "account.payment":
            return res
        payments = self.env["account.payment"].browse(
            self.env.context.get("active_ids", [])
        ).exists()
        payments._xtd_validate_for_remesa()
        res.update(
            {
                "payment_ids": [Command.set(payments.ids)],
                "company_id": payments[0].company_id.id,
                "journal_id": payments[0].journal_id.id,
                "payment_method_line_id": payments[0].payment_method_line_id.id,
                "currency_id": payments[0].currency_id.id,
            }
        )
        return res

    def action_create_remesa(self):
        self.ensure_one()
        self.payment_ids._xtd_validate_for_remesa()
        remesa = self.env["account.payment.remesa"].create(
            {
                "date": self.date,
                "company_id": self.company_id.id,
                "journal_id": self.journal_id.id,
                "payment_method_line_id": self.payment_method_line_id.id,
                "payment_ids": [Command.set(self.payment_ids.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.remesa",
            "views": [(False, "form")],
            "res_id": remesa.id,
            "target": "current",
        }

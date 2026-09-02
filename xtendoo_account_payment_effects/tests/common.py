from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class XtdAccountPaymentEffectsCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.company_data["company"]
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.bank_journal.suspense_account_id = (
            cls.company.account_journal_suspense_account_id
        )
        cls.env.user.write(
            {
                "group_ids": [
                    Command.link(
                        cls.env.ref("account_payment_batch_oca.group_account_payment").id
                    )
                ]
            }
        )
        cls.check_method = cls._create_effect_method(
            name="Customer Check",
            code="xtd_manual_check",
            due_date_required=False,
        )
        cls.note_method = cls._create_effect_method(
            name="Promissory Note",
            code="xtd_manual_note",
            due_date_required=True,
        )

    @classmethod
    def _create_effect_method(cls, name, code, due_date_required=False):
        method = cls.env["account.payment.method"].sudo().create(
            {
                "name": name,
                "code": code,
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        return cls.env["account.payment.method.line"].create(
            {
                "name": name,
                "journal_id": cls.bank_journal.id,
                "payment_method_id": method.id,
                "company_id": cls.company.id,
                "selectable": True,
                "payment_order_ok": True,
                "bank_account_link": "fixed",
                "payment_account_id": cls.inbound_payment_method_line.payment_account_id.id,
                "xtd_manage_effects": True,
                "xtd_effect_reference_required": True,
                "xtd_effect_due_date_required": due_date_required,
            }
        )

    @classmethod
    def _create_invoice(cls, partner, amount, currency=False, post=True):
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "currency_id": (currency or cls.company.currency_id).id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": f"Invoice line {amount}",
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        if post:
            invoice.action_post()
        return invoice

    def _register_effect_payment(
        self,
        invoices,
        payment_method_line,
        amount=False,
        payment_reference="REF-001",
        due_date=False,
        group_payment=False,
        currency=False,
    ):
        invoices = invoices if hasattr(invoices, "ids") else self.env["account.move"].browse(invoices)
        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoices.ids,
        ).create(
            {
                "amount": amount or sum(invoices.mapped("amount_residual")),
                "group_payment": group_payment,
                "currency_id": (currency or invoices[0].currency_id).id,
                "payment_method_line_id": payment_method_line.id,
                "journal_id": self.bank_journal.id,
                "xtd_payment_reference": payment_reference,
                "xtd_effect_due_date": due_date,
            }
        )
        return wizard._create_payments()

    def _create_statement_line(self, amount, date=False):
        statement = self.env["account.bank.statement"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": date or "2026-08-28",
                "name": "XTD-STMT",
            }
        )
        return self.env["account.bank.statement.line"].create(
            {
                "name": "XTD-STMT-LINE",
                "payment_ref": "BANK DEPOSIT",
                "journal_id": self.bank_journal.id,
                "statement_id": statement.id,
                "amount": amount,
                "date": date or "2026-08-28",
            }
        )

    @classmethod
    def _create_company_data(cls, name="Other Company"):
        company = cls.env["res.company"].create(
            {
                "name": name,
                "country_id": cls.company.account_fiscal_country_id.id,
            }
        )
        cls.env.user.write({"company_ids": [Command.link(company.id)]})
        cls._use_chart_template(company)
        company_data = cls.collect_company_accounting_data(company)
        company_data["default_journal_bank"].suspense_account_id = (
            company.account_journal_suspense_account_id
        )
        return company_data

    @classmethod
    def _create_effect_method_for_company(
        cls, company_data, name, code, due_date_required=False
    ):
        method = cls.env["account.payment.method"].sudo().create(
            {
                "name": name,
                "code": code,
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        return cls.env["account.payment.method.line"].with_company(
            company_data["company"]
        ).create(
            {
                "name": name,
                "journal_id": company_data["default_journal_bank"].id,
                "payment_method_id": method.id,
                "company_id": company_data["company"].id,
                "selectable": True,
                "payment_order_ok": True,
                "bank_account_link": "fixed",
                "payment_account_id": cls.env[
                    "account.chart.template"
                ]
                .with_company(company_data["company"])
                .ref("account_journal_payment_debit_account_id")
                .id,
                "xtd_manage_effects": True,
                "xtd_effect_reference_required": True,
                "xtd_effect_due_date_required": due_date_required,
            }
        )

    @classmethod
    def _create_invoice_for_company(
        cls, company_data, partner, amount, currency=False, post=True
    ):
        invoice = (
            cls.env["account.move"]
            .with_company(company_data["company"])
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "currency_id": (
                        currency or company_data["company"].currency_id
                    ).id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": f"Invoice line {amount}",
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )
        if post:
            invoice.action_post()
        return invoice

    def _register_effect_payment_for_company(
        self,
        company_data,
        invoices,
        payment_method_line,
        amount=False,
        payment_reference="REF-OTHER-001",
        due_date=False,
        group_payment=False,
    ):
        invoices = invoices if hasattr(invoices, "ids") else self.env["account.move"].browse(invoices)
        wizard = (
            self.env["account.payment.register"]
            .with_company(company_data["company"])
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create(
                {
                    "amount": amount or sum(invoices.mapped("amount_residual")),
                    "group_payment": group_payment,
                    "payment_method_line_id": payment_method_line.id,
                    "journal_id": company_data["default_journal_bank"].id,
                    "xtd_payment_reference": payment_reference,
                    "xtd_effect_due_date": due_date,
                }
            )
        )
        return wizard._create_payments()

    def _create_lot_from_payments(self, payments, date="2026-08-28"):
        wizard = self.env["xtd.account.payment.lot.create.wizard"].with_context(
            active_model="account.payment",
            active_ids=payments.ids,
        ).create({"date": date})
        wizard.action_create_lot()
        return payments.payment_lot_id

    def _select_lot_in_reconcile_form(self, statement_line, lot):
        with Form(
            statement_line,
            view="account_reconcile_oca.bank_statement_line_form_reconcile_view",
        ) as form:
            form.xtd_payment_lot_id = lot





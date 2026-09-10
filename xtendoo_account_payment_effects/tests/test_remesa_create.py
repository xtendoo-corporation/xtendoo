from odoo.exceptions import UserError

from .common import XtdAccountPaymentEffectsCommon


class TestRemesaCreate(XtdAccountPaymentEffectsCommon):
    def _create_three_check_payments(self):
        invoices = [
            self._create_invoice(self.partner_a, 1000.0),
            self._create_invoice(self.partner_b, 500.0),
            self._create_invoice(self.partner_a, 750.0),
        ]
        references = ["CH-001", "CH-002", "CH-003"]
        payments = self.env["account.payment"]
        for invoice, reference in zip(invoices, references):
            payments |= self._register_effect_payment(
                invoice,
                self.check_method,
                amount=invoice.amount_total,
                payment_reference=reference,
            )
        return payments, invoices

    def test_create_remesa_from_existing_payments_without_new_payments_or_moves(self):
        payments, _invoices = self._create_three_check_payments()
        moves_before = self.env["account.move"].search_count(
            [("id", "in", payments.move_id.ids)]
        )
        payment_count_before = self.env["account.payment"].search_count(
            [("id", "in", payments.ids)]
        )
        remesa = self._create_remesa(payments)
        self.assertEqual(
            self.env["account.payment"].search_count([("id", "in", payments.ids)]),
            payment_count_before,
        )
        self.assertEqual(
            self.env["account.move"].search_count([("id", "in", payments.move_id.ids)]),
            moves_before,
        )
        self.assertEqual(remesa.payment_count, 3)
        self.assertEqual(remesa.amount_total, 2250.0)
        self.assertEqual(len(remesa.payment_ids), 3)
        self.assertEqual(remesa.state, "draft")
        self.assertTrue(all(payment.xtd_remesa_id == remesa for payment in payments))

    def test_wizard_prefills_from_selected_payments(self):
        payments, _invoices = self._create_three_check_payments()
        remesa = self._create_remesa_from_wizard(payments)
        self.assertEqual(remesa.payment_count, 3)
        self.assertEqual(remesa.payment_method_line_id, self.check_method)
        self.assertEqual(remesa.journal_id, self.bank_journal)

    def test_payment_already_in_remesa_fails(self):
        payments, _invoices = self._create_three_check_payments()
        self._create_remesa(payments[:1])
        with self.assertRaises(UserError):
            self.env["account.payment.remesa"].create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.check_method.id,
                    "payment_ids": [(4, payments[0].id)],
                }
            )

    def test_payment_already_matched_fails(self):
        payments, _invoices = self._create_three_check_payments()
        remesa = self._create_remesa(payments[:1])
        remesa.action_confirm()
        with self.assertRaises(UserError):
            self.env["account.payment.remesa"].create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.check_method.id,
                    "payment_ids": [(4, payments[0].id)],
                }
            )

    def test_mixing_currencies_fails(self):
        alt_currency = self.env.ref("base.EUR")
        if alt_currency == self.company.currency_id:
            alt_currency = self.env.ref("base.USD")
        alt_currency.sudo().write({"active": True})
        invoice_eur = self._create_invoice(self.partner_a, 100.0)
        payment_eur = self._register_effect_payment(
            invoice_eur,
            self.check_method,
            amount=100.0,
            payment_reference="CH-EUR",
        )

        usd_journal = self.env["account.journal"].create(
            {
                "name": "USD Bank XTD",
                "type": "bank",
                "code": "XUSD",
                "currency_id": alt_currency.id,
                "company_id": self.company.id,
            }
        )
        usd_journal.suspense_account_id = self.company.account_journal_suspense_account_id
        usd_method = self._create_effect_method(
            name="Customer Check USD",
            code="xtd_manual_check_usd",
            journal=usd_journal,
        )
        invoice_usd = self._create_invoice(
            self.partner_a,
            100.0,
            currency=alt_currency,
        )
        payment_usd = self._register_effect_payment(
            invoice_usd,
            usd_method,
            amount=100.0,
            currency=alt_currency,
            payment_reference="CH-USD",
        )
        self.assertNotEqual(payment_eur.currency_id, payment_usd.currency_id)
        with self.assertRaises(UserError):
            self.env["account.payment.remesa"].create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.check_method.id,
                    "payment_ids": [(4, payment_eur.id), (4, payment_usd.id)],
                }
            )

    def test_mixing_payment_methods_fails(self):
        invoice_1 = self._create_invoice(self.partner_a, 100.0)
        invoice_2 = self._create_invoice(self.partner_a, 100.0)
        payment_1 = self._register_effect_payment(
            invoice_1,
            self.check_method,
            amount=100.0,
            payment_reference="CH-M1",
        )
        payment_2 = self._register_effect_payment(
            invoice_2,
            self.note_method,
            amount=100.0,
            payment_reference="PG-M2",
            due_date="2026-09-30",
        )
        with self.assertRaises(UserError):
            self.env["account.payment.remesa"].create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.check_method.id,
                    "payment_ids": [(4, payment_1.id), (4, payment_2.id)],
                }
            )

    def test_mixing_companies_fails(self):
        other_company_data = self._create_company_data()
        other_method = self._create_effect_method_for_company(
            other_company_data,
            name="Other Check",
            code="xtd_other_check",
        )
        invoice_1 = self._create_invoice(self.partner_a, 100.0)
        invoice_2 = self._create_invoice_for_company(
            other_company_data,
            self.partner_a,
            100.0,
        )
        payment_1 = self._register_effect_payment(
            invoice_1,
            self.check_method,
            amount=100.0,
            payment_reference="CH-C1",
        )
        payment_2 = self._register_effect_payment_for_company(
            other_company_data,
            invoice_2,
            other_method,
            amount=100.0,
            payment_reference="CH-C2",
        )
        with self.assertRaises(UserError):
            self.env["account.payment.remesa"].create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.check_method.id,
                    "payment_ids": [(4, payment_1.id), (4, payment_2.id)],
                }
            )

    def test_confirm_requires_payments(self):
        remesa = self.env["account.payment.remesa"].create(
            {
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "payment_method_line_id": self.check_method.id,
            }
        )
        with self.assertRaises(UserError):
            remesa.action_confirm()

from odoo.exceptions import UserError

from .common import XtdAccountPaymentEffectsCommon


class TestExistingPaymentLot(XtdAccountPaymentEffectsCommon):
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

    def test_create_lot_from_existing_payments_without_new_payments_or_moves(self):
        payments, _invoices = self._create_three_check_payments()
        moves_before = self.env["account.move"].search_count(
            [("id", "in", payments.move_id.ids)]
        )
        payment_count_before = self.env["account.payment"].search_count(
            [("id", "in", payments.ids)]
        )
        lot = self._create_lot_from_payments(payments)
        self.assertEqual(
            self.env["account.payment"].search_count([("id", "in", payments.ids)]),
            payment_count_before,
        )
        self.assertEqual(
            self.env["account.move"].search_count([("id", "in", payments.move_id.ids)]),
            moves_before,
        )
        self.assertEqual(lot.payment_count, 3)
        self.assertEqual(lot.amount, 2250.0)
        self.assertEqual(len(lot.payment_ids), 3)
        self.assertEqual(lot.order_id.xtd_source_type, "existing_payments")
        self.assertTrue(all(payment.payment_lot_id == lot for payment in payments))

    def test_payment_already_in_lot_fails(self):
        payments, _invoices = self._create_three_check_payments()
        self._create_lot_from_payments(payments[:1])
        with self.assertRaises(UserError):
            self._create_lot_from_payments(payments[:1])

    def test_payment_already_matched_fails(self):
        payments, _invoices = self._create_three_check_payments()
        lot = self._create_lot_from_payments(payments[:1])
        statement_line = self._create_statement_line(1000.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        with self.assertRaises(UserError):
            self._create_lot_from_payments(payments[:1])

    def test_mixing_currencies_fails(self):
        alt_currency = self.env.ref("base.EUR")
        if alt_currency == self.company.currency_id:
            alt_currency = self.env.ref("base.USD")
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
        usd_method_def = self.env["account.payment.method"].sudo().create(
            {
                "name": "Customer Check USD",
                "code": "xtd_manual_check_usd",
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        usd_method = self.env["account.payment.method.line"].create(
            {
                "name": "Customer Check USD",
                "journal_id": usd_journal.id,
                "payment_method_id": usd_method_def.id,
                "company_id": self.company.id,
                "selectable": True,
                "payment_order_ok": True,
                "bank_account_link": "fixed",
                "payment_account_id": self.inbound_payment_method_line.payment_account_id.id,
                "xtd_manage_effects": True,
                "xtd_effect_reference_required": True,
            }
        )
        invoice_usd = self._create_invoice(
            self.partner_a,
            100.0,
            currency=alt_currency,
        )
        payment_usd = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoice_usd.ids,
        ).create(
            {
                "amount": 100.0,
                "currency_id": alt_currency.id,
                "payment_method_line_id": usd_method.id,
                "journal_id": usd_journal.id,
                "xtd_payment_reference": "CH-USD",
            }
        )._create_payments()
        self.assertNotEqual(payment_eur.currency_id, payment_usd.currency_id)
        with self.assertRaises(UserError):
            self._create_lot_from_payments(payment_eur + payment_usd)

    def test_mixing_methods_fails(self):
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
            self._create_lot_from_payments(payment_1 + payment_2)

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
            self._create_lot_from_payments(payment_1 + payment_2)




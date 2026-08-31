from odoo.exceptions import UserError, ValidationError

from .common import XtdAccountPaymentEffectsCommon


class TestEffectPayment(XtdAccountPaymentEffectsCommon):
    def test_register_check(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payments = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-001",
        )
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.payment_reference, "CH-001")
        self.assertFalse(payments.xtd_effect_due_date)
        self.assertEqual(invoice.payment_state, "in_payment")
        self.assertTrue(payments.is_reconciled)
        self.assertFalse(payments.is_matched)
        self.assertEqual(payments.xtd_effect_status, "portfolio")

    def test_register_promissory_note_requires_due_date(self):
        invoice = self._create_invoice(self.partner_a, 4500.0)
        with self.assertRaises(UserError):
            self._register_effect_payment(
                invoice,
                self.note_method,
                amount=4500.0,
                payment_reference="PAG-4587",
            )
        payments = self._register_effect_payment(
            invoice,
            self.note_method,
            amount=4500.0,
            payment_reference="PAG-4587",
            due_date="2026-09-30",
        )
        self.assertEqual(payments.xtd_effect_due_date.isoformat(), "2026-09-30")
        self.assertEqual(invoice.payment_state, "in_payment")

    def test_reference_required(self):
        invoice = self._create_invoice(self.partner_a, 1200.0)
        with self.assertRaises(UserError):
            self._register_effect_payment(
                invoice,
                self.check_method,
                amount=1200.0,
                payment_reference=False,
            )

    def test_partial_payment_does_not_force_paid(self):
        invoice = self._create_invoice(self.partner_a, 3000.0)
        payments = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-PART",
        )
        self.assertEqual(len(payments), 1)
        self.assertNotEqual(invoice.payment_state, "paid")
        self.assertGreater(invoice.amount_residual, 0)
        self.assertFalse(payments.is_matched)

    def test_one_invoice_several_payments(self):
        invoice = self._create_invoice(self.partner_a, 3000.0)
        payment_1 = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-1000",
        )
        payment_2 = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=2000.0,
            payment_reference="CH-2000",
        )
        self.assertEqual(len(payment_1 + payment_2), 2)
        self.assertEqual(invoice.payment_state, "in_payment")
        self.assertFalse((payment_1 + payment_2).filtered("is_matched"))

    def test_one_payment_for_multiple_invoices(self):
        invoice_1 = self._create_invoice(self.partner_a, 1000.0)
        invoice_2 = self._create_invoice(self.partner_a, 2000.0)
        payments = self._register_effect_payment(
            invoice_1 + invoice_2,
            self.check_method,
            amount=3000.0,
            payment_reference="CH-GROUP",
            group_payment=True,
        )
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.payment_reference, "CH-GROUP")
        self.assertEqual(payments.reconciled_invoices_count, 2)
        self.assertEqual(invoice_1.payment_state, "in_payment")
        self.assertEqual(invoice_2.payment_state, "in_payment")

    def test_manage_effect_method_configuration_constraints(self):
        with self.assertRaises(ValidationError):
            self.env["account.payment.method.line"].create(
                {
                    "name": "Broken Effect Method",
                    "journal_id": self.bank_journal.id,
                    "payment_method_id": self.check_method.payment_method_id.id,
                    "company_id": self.company.id,
                    "selectable": True,
                    "payment_order_ok": False,
                    "bank_account_link": "fixed",
                    "xtd_manage_effects": True,
                    "payment_account_id": self.inbound_payment_method_line.payment_account_id.id,
                }
            )


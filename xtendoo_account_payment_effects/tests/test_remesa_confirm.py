from odoo.exceptions import UserError

from .common import XtdAccountPaymentEffectsCommon


class TestRemesaConfirm(XtdAccountPaymentEffectsCommon):
    def _create_three_invoices_and_payments(self):
        invoices = [
            self._create_invoice(self.partner_a, 1000.0),
            self._create_invoice(self.partner_b, 500.0),
            self._create_invoice(self.partner_a, 750.0),
        ]
        payments = self.env["account.payment"]
        for invoice, reference in zip(invoices, ["CH-001", "CH-002", "CH-003"]):
            payments |= self._register_effect_payment(
                invoice,
                self.check_method,
                amount=invoice.amount_total,
                payment_reference=reference,
            )
        return invoices, payments

    def test_confirm_remesa_matches_payments_and_pays_invoices(self):
        invoices, payments = self._create_three_invoices_and_payments()
        remesa = self._create_remesa(payments)
        remesa.action_confirm()
        payments.invalidate_recordset()
        remesa.invalidate_recordset()
        self.assertEqual(remesa.state, "confirmed")
        self.assertTrue(remesa.statement_line_id)
        self.assertEqual(remesa.statement_line_id.amount, 2250.0)
        for payment in payments:
            self.assertTrue(payment.is_matched)
            self.assertEqual(payment.state, "paid")
        for invoice in invoices:
            invoice.invalidate_recordset()
            self.assertEqual(invoice.payment_state, "paid")

    def test_overdue_filter_domain(self):
        invoice = self._create_invoice(self.partner_a, 100.0)
        payment = self._register_effect_payment(
            invoice,
            self.note_method,
            amount=100.0,
            payment_reference="PG-OVERDUE",
            due_date="2020-01-01",
        )
        overdue = self.env["account.payment"].search(
            [
                ("id", "=", payment.id),
                ("payment_type", "=", "inbound"),
                ("partner_type", "=", "customer"),
                ("payment_method_line_id.xtd_manage_effects", "=", True),
                ("xtd_effect_due_date", "<", "2026-08-26"),
            ]
        )
        self.assertEqual(overdue, payment)

    def test_confirm_twice_is_blocked(self):
        _invoices, payments = self._create_three_invoices_and_payments()
        remesa = self._create_remesa(payments)
        remesa.action_confirm()
        with self.assertRaises(UserError):
            remesa.action_confirm()

    def test_rejected_effect_uses_standard_state(self):
        invoice = self._create_invoice(self.partner_a, 250.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=250.0,
            payment_reference="CH-REJECT",
        )
        payment.action_reject()
        invoice.invalidate_recordset()
        self.assertEqual(payment.state, "rejected")
        self.assertEqual(payment.xtd_effect_status, "rejected")

    def test_reject_matched_effect_is_blocked(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-MATCHED",
        )
        remesa = self._create_remesa(payment)
        remesa.action_confirm()
        payment.invalidate_recordset()
        self.assertTrue(payment.is_matched)
        with self.assertRaises(UserError):
            payment.action_reject()

    def test_cancel_matched_effect_is_blocked(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-MATCHED2",
        )
        remesa = self._create_remesa(payment)
        remesa.action_confirm()
        payment.invalidate_recordset()
        self.assertTrue(payment.is_matched)
        move_id = payment.move_id
        with self.assertRaises(UserError):
            payment.action_cancel()
        payment.invalidate_recordset()
        self.assertEqual(payment.move_id, move_id)
        self.assertTrue(payment.is_matched)

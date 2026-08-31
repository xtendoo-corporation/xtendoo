from .common import XtdAccountPaymentEffectsCommon


class TestLotReconcile(XtdAccountPaymentEffectsCommon):
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

    def test_lot_reconciliation(self):
        invoices, payments = self._create_three_invoices_and_payments()
        lot = self._create_lot_from_payments(payments)
        statement_line = self._create_statement_line(2250.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        payments.invalidate_recordset()
        lot.invalidate_recordset()
        for payment in payments:
            self.assertTrue(payment.is_matched)
            self.assertEqual(payment.state, "paid")
        self.assertTrue(lot.xtd_is_matched)
        for invoice in invoices:
            invoice.invalidate_recordset()
            self.assertEqual(invoice.payment_state, "paid")

    def test_lot_partially_reconciled_is_not_fully_matched(self):
        invoice_1 = self._create_invoice(self.partner_a, 100.0)
        invoice_2 = self._create_invoice(self.partner_a, 150.0)
        payments = self._register_effect_payment(
            invoice_1,
            self.check_method,
            amount=100.0,
            payment_reference="CH-P1",
        ) | self._register_effect_payment(
            invoice_2,
            self.check_method,
            amount=150.0,
            payment_reference="CH-P2",
        )
        lot = self._create_lot_from_payments(payments)
        statement_line = self._create_statement_line(100.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        payments.invalidate_recordset()
        lot.invalidate_recordset()
        self.assertFalse(lot.xtd_is_matched)
        self.assertEqual(len(payments.filtered("is_matched")), 1)

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

    def test_lot_move_lines_to_reconcile_only_returns_pending_lines(self):
        invoices, payments = self._create_three_invoices_and_payments()
        lot = self._create_lot_from_payments(payments)
        lines = lot._get_move_lines_to_reconcile()
        self.assertTrue(lines)
        self.assertEqual(len(lines), 3)
        statement_line = self._create_statement_line(2250.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        lot.invalidate_recordset()
        self.assertFalse(lot._get_move_lines_to_reconcile())


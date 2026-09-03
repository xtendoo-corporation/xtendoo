from odoo.exceptions import UserError
from odoo.tests import Form

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

    def test_import_existing_payments_populates_order_inline(self):
        payments, _invoices = self._create_three_check_payments()
        already_lotted = payments[0]
        self._create_lot_from_payments(already_lotted)
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        self.assertEqual(order.xtd_source_type, "oca")
        order.xtd_action_import_existing_payments()
        self.assertEqual(order.xtd_source_type, "existing_payments")
        self.assertEqual(order.xtd_existing_payment_ids, payments - already_lotted)
        self.assertTrue(order.xtd_deposit_date)

    def test_xtd_bank_journal_id_defaults_from_payment_method(self):
        with Form(
            self.env["account.payment.order"].with_context(
                default_payment_type="inbound", default_company_id=self.company.id
            )
        ) as form:
            form.payment_method_line_id = self.check_method
        order = form.save()
        self.assertEqual(order.xtd_bank_journal_id, self.check_method.journal_id)

    def test_import_existing_payments_requires_bank_journal(self):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
            }
        )
        with self.assertRaises(UserError):
            order.xtd_action_import_existing_payments()

    def test_import_existing_payments_uses_selected_bank_journal(self):
        payments, _invoices = self._create_three_check_payments()

        other_journal = self.env["account.journal"].create(
            {
                "name": "Other Bank XTD",
                "type": "bank",
                "code": "XOTH2",
                "currency_id": self.company.currency_id.id,
                "company_id": self.company.id,
            }
        )
        other_journal.suspense_account_id = (
            self.company.account_journal_suspense_account_id
        )
        other_method_def = self.env["account.payment.method"].sudo().create(
            {
                "name": "Other Journal Check 2",
                "code": "xtd_other_journal_check_2",
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        other_method = self.env["account.payment.method.line"].create(
            {
                "name": "Other Journal Check 2",
                "journal_id": other_journal.id,
                "payment_method_id": other_method_def.id,
                "company_id": self.company.id,
                "selectable": True,
                "payment_order_ok": True,
                "bank_account_link": "fixed",
                "payment_account_id": self.inbound_payment_method_line.payment_account_id.id,
                "xtd_manage_effects": True,
                "xtd_effect_reference_required": True,
            }
        )
        invoice_other = self._create_invoice(self.partner_a, 300.0)
        payment_other = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoice_other.ids,
        ).create(
            {
                "amount": 300.0,
                "payment_method_line_id": other_method.id,
                "journal_id": other_journal.id,
                "xtd_payment_reference": "CH-OTHJ2",
            }
        )._create_payments()

        # Order's own payment method points to bank_journal, but the user
        # picks a different destination bank journal for the deposit.
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": other_journal.id,
            }
        )
        order.xtd_action_import_existing_payments()
        self.assertEqual(order.journal_id, other_journal)
        self.assertEqual(order.xtd_existing_payment_ids, payment_other)
        self.assertFalse(set(payments.ids) & set(order.xtd_existing_payment_ids.ids))

    def test_import_existing_payments_includes_other_methods_sharing_journal(self):
        payments, _invoices = self._create_three_check_payments()
        note_invoice = self._create_invoice(self.partner_a, 400.0)
        note_payment = self._register_effect_payment(
            note_invoice,
            self.note_method,
            amount=400.0,
            payment_reference="PG-INLINE",
            due_date="2026-09-30",
        )
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        order.xtd_action_import_existing_payments()
        self.assertEqual(order.xtd_existing_payment_ids, payments + note_payment)

    def test_create_lot_from_order_inline_payments(self):
        payments, _invoices = self._create_three_check_payments()
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        order.xtd_action_import_existing_payments()
        order.xtd_action_confirm_existing_payments()
        self.assertEqual(order.state, "uploaded")
        self.assertFalse(order.xtd_existing_payment_ids)
        self.assertEqual(len(order.payment_ids), 3)
        self.assertTrue(
            all(payment.payment_lot_id.order_id == order for payment in payments)
        )

    def test_confirm_rejects_payments_from_a_different_journal(self):
        payments, _invoices = self._create_three_check_payments()
        other_journal = self.env["account.journal"].create(
            {
                "name": "Other Bank XTD",
                "type": "bank",
                "code": "XOTH",
                "currency_id": self.company.currency_id.id,
                "company_id": self.company.id,
            }
        )
        other_journal.suspense_account_id = (
            self.company.account_journal_suspense_account_id
        )
        other_method_def = self.env["account.payment.method"].sudo().create(
            {
                "name": "Other Journal Check",
                "code": "xtd_other_journal_check",
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        other_method = self.env["account.payment.method.line"].create(
            {
                "name": "Other Journal Check",
                "journal_id": other_journal.id,
                "payment_method_id": other_method_def.id,
                "company_id": self.company.id,
                "selectable": True,
                "payment_order_ok": True,
                "bank_account_link": "fixed",
                "payment_account_id": self.inbound_payment_method_line.payment_account_id.id,
                "xtd_manage_effects": True,
                "xtd_effect_reference_required": True,
            }
        )
        invoice_other = self._create_invoice(self.partner_a, 300.0)
        payment_other = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoice_other.ids,
        ).create(
            {
                "amount": 300.0,
                "payment_method_line_id": other_method.id,
                "journal_id": other_journal.id,
                "xtd_payment_reference": "CH-OTHJ",
            }
        )._create_payments()

        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        order.xtd_action_import_existing_payments()
        # Force in a payment from a different journal, bypassing the tab's own
        # domain, to prove the server-side safeguard still holds.
        order.xtd_existing_payment_ids = [(4, payment_other.id)]
        with self.assertRaises(UserError):
            order.xtd_action_confirm_existing_payments()

    def test_create_lot_from_order_inline_requires_selection(self):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        with self.assertRaises(UserError):
            order.xtd_action_confirm_existing_payments()

    def test_import_existing_payments_requires_draft_order(self):
        payments, _invoices = self._create_three_check_payments()
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_method_line_id": self.check_method.id,
                "company_id": self.company.id,
                "journal_id": self.bank_journal.id,
                "xtd_bank_journal_id": self.bank_journal.id,
            }
        )
        order.xtd_action_import_existing_payments()
        order.xtd_action_confirm_existing_payments()
        self.assertEqual(order.state, "uploaded")
        with self.assertRaises(UserError):
            order.xtd_action_import_existing_payments()

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

    def test_mixing_methods_succeeds(self):
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
        lot = self._create_lot_from_payments(payment_1 + payment_2)
        self.assertEqual(lot.payment_count, 2)
        self.assertEqual(
            (payment_1 + payment_2).payment_method_line_id,
            self.check_method + self.note_method,
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
            self._create_lot_from_payments(payment_1 + payment_2)




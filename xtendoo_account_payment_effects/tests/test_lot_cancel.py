from odoo import Command
from odoo.exceptions import UserError

from .common import XtdAccountPaymentEffectsCommon


class TestLotCancel(XtdAccountPaymentEffectsCommon):
    def _create_xtd_lot(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-CANCEL",
        )
        lot = self._create_lot_from_payments(payment)
        return invoice, payment, lot, lot.order_id

    def test_cancel_lot_does_not_cancel_payments(self):
        invoice, payment, lot, order = self._create_xtd_lot()
        move_id = payment.move_id
        order.action_cancel()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertTrue(payment.exists())
        self.assertEqual(payment.state, "in_process")
        self.assertEqual(payment.move_id, move_id)
        self.assertFalse(payment.payment_lot_id)
        self.assertFalse(payment.payment_order_id)
        self.assertEqual(invoice.payment_state, "in_payment")
        self.assertEqual(order.state, "cancel")
        self.assertFalse(lot.exists())

    def test_cancel2draft_protection_keeps_existing_payments(self):
        _invoice, payment, _lot, order = self._create_xtd_lot()
        order.action_cancel()
        order.cancel2draft()
        payment.invalidate_recordset()
        self.assertTrue(payment.exists())
        self.assertEqual(payment.state, "in_process")
        self.assertFalse(payment.payment_order_id)
        self.assertEqual(order.state, "draft")

    def test_cancel_reconciled_lot_is_blocked(self):
        invoice, payment, lot, order = self._create_xtd_lot()
        statement_line = self._create_statement_line(1000.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertTrue(payment.is_matched)
        self.assertEqual(invoice.payment_state, "paid")
        with self.assertRaises(UserError):
            order.action_cancel()

    def test_rejected_effect_uses_standard_state(self):
        invoice = self._create_invoice(self.partner_a, 250.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=250.0,
            payment_reference="CH-REJECT",
        )
        payment.is_sent = True
        payment.action_reject()
        invoice.invalidate_recordset()
        self.assertEqual(payment.state, "rejected")
        self.assertEqual(payment.xtd_effect_status, "rejected")

    def test_reject_matched_effect_is_blocked(self):
        invoice, payment, lot, _order = self._create_xtd_lot()
        statement_line = self._create_statement_line(1000.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertTrue(payment.is_matched)
        payment.is_sent = True
        with self.assertRaises(UserError):
            payment.action_reject()

    def test_cancel_matched_effect_is_blocked(self):
        invoice, payment, lot, _order = self._create_xtd_lot()
        statement_line = self._create_statement_line(1000.0)
        self._select_lot_in_reconcile_form(statement_line, lot)
        statement_line.reconcile_bank_line()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertTrue(payment.is_matched)
        move_id = payment.move_id
        with self.assertRaises(UserError):
            payment.action_cancel()
        payment.invalidate_recordset()
        self.assertEqual(payment.move_id, move_id)
        self.assertTrue(payment.is_matched)

    def test_original_oca_flow_still_works(self):
        payment_method = self.env["account.payment.method"].sudo().create(
            {
                "name": "OCA Inbound",
                "code": "xtd_oca_inbound",
                "payment_type": "inbound",
                "payment_order_ok": True,
            }
        )
        inbound_mode = self.env["account.payment.method.line"].create(
            {
                "name": "OCA Inbound",
                "journal_id": self.bank_journal.id,
                "payment_method_id": payment_method.id,
                "company_id": self.company.id,
                "selectable": True,
                "payment_order_ok": True,
                "mail_notif": False,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_a.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "preferred_payment_method_line_id": inbound_mode.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "product that cost 100",
                            "quantity": 1,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "price_unit": 100.0,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        action = invoice.create_account_payment_line()
        self.assertTrue(action)
        order = self.env["account.payment.order"].search(
            [
                ("payment_type", "=", "inbound"),
                ("payment_method_line_id", "=", inbound_mode.id),
                ("state", "=", "draft"),
            ],
            limit=1,
        )
        self.assertTrue(order)
        order.draft2open()
        self.assertEqual(order.payment_count, 1)
        self.assertEqual(order.xtd_source_type, "oca")


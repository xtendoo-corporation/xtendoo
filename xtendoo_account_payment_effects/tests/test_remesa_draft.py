from odoo.exceptions import UserError

from .common import XtdAccountPaymentEffectsCommon


class TestRemesaDraft(XtdAccountPaymentEffectsCommon):
    def _create_confirmed_remesa(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-DRAFT",
        )
        remesa = self._create_remesa(payment)
        remesa.action_confirm()
        return invoice, payment, remesa

    def test_action_draft_undoes_confirmation(self):
        invoice, payment, remesa = self._create_confirmed_remesa()
        statement_line = remesa.statement_line_id
        remesa.action_draft()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertEqual(remesa.state, "draft")
        self.assertFalse(remesa.statement_line_id)
        self.assertFalse(statement_line.exists())
        self.assertFalse(payment.is_matched)
        self.assertEqual(payment.state, "in_process")
        self.assertEqual(invoice.payment_state, "in_payment")
        # the payment stays linked to the remesa, ready to confirm again
        self.assertEqual(payment.xtd_remesa_id, remesa)

    def test_action_draft_on_draft_remesa_is_blocked(self):
        invoice = self._create_invoice(self.partner_a, 1000.0)
        payment = self._register_effect_payment(
            invoice,
            self.check_method,
            amount=1000.0,
            payment_reference="CH-STILL-DRAFT",
        )
        remesa = self._create_remesa(payment)
        with self.assertRaises(UserError):
            remesa.action_draft()

    def test_can_confirm_again_after_reset_to_draft(self):
        invoice, payment, remesa = self._create_confirmed_remesa()
        remesa.action_draft()
        remesa.action_confirm()
        payment.invalidate_recordset()
        invoice.invalidate_recordset()
        self.assertEqual(remesa.state, "confirmed")
        self.assertTrue(payment.is_matched)
        self.assertEqual(invoice.payment_state, "paid")

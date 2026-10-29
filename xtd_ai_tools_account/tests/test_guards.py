from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestAccountGuards(XtdAiAccountCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run(self.biller)
        self.move = self.make_move(
            "out_invoice", self.customer, 100, "2026-07-31", post=False
        )
        self.agent_move = self.tool_env(self.biller, self.run)["account.move"].browse(
            self.move.id
        )

    def test_move_methods_blocked_in_run(self):
        for method in (
            "action_post",
            "_post",
            "button_cancel",
            "action_register_payment",
            "unlink",
        ):
            with self.assertRaises(XtdAiDraftOnlyError, msg=method):
                getattr(self.agent_move, method)()
        self.assertEqual(self.move.state, "draft")
        self.assertTrue(self.move.exists())

    def test_empty_recordsets_are_not_blocked(self):
        # Some Odoo builds call payment_ids.unlink() -> move_id.unlink() on empty
        # sets while creating invoice lines: an empty call must never trip a guard
        # (seen in pre-aicia: every vendor bill failed with draft_only).
        env = self.tool_env(self.biller, self.run)
        env["account.move"].unlink()
        env["account.move"].button_cancel()
        env["account.payment"].unlink()
        env["account.payment"].action_post()
        env["account.payment"].create([])
        env["res.partner"].unlink()
        env["mail.mail"].create([])

    def test_move_methods_work_without_run(self):
        move = self.move.with_user(self.biller)
        move.action_post()
        self.assertEqual(self.move.state, "posted")
        other = self.make_move(
            "out_invoice", self.customer, 5, "2026-07-31", post=False
        )
        other.with_user(self.biller).unlink()
        self.assertFalse(other.exists())

    def test_payment_guards(self):
        payment_model = self.tool_env(self.biller, self.run)["account.payment"]
        with self.assertRaises(XtdAiDraftOnlyError):
            payment_model.create({"partner_id": self.customer.id, "amount": 1.0})
        payment = self.env["account.payment"].create(
            {"partner_id": self.customer.id, "amount": 1.0}
        )
        with self.assertRaises(XtdAiDraftOnlyError):
            payment_model.browse(payment.id).action_post()
        self.assertEqual(payment.state, "draft")
        payment.action_post()  # normal behaviour without run
        self.assertNotEqual(payment.state, "draft")

    def test_creating_draft_triggers_no_guard_and_auto_post_is_off(self):
        structured = self.call_create(self.biller, self.run)
        self.assertEqual(structured["status"], "ok", structured)
        move = self.env["account.move"].browse(structured["records"][0]["id"])
        self.assertEqual((move.state, move.auto_post), ("draft", "no"))
        # The auto-post cron only picks drafts with auto_post != 'no'
        pending_autopost = self.env["account.move"].search(
            [("state", "=", "draft"), ("auto_post", "!=", "no")]
        )
        self.assertNotIn(move, pending_autopost)

    def call_create(self, user, run):
        self.set_confirm(user, False)
        return self.agent_call(
            user,
            run,
            "create_customer_invoice",
            {
                "partner_id": self.customer.id,
                "lines": [
                    {"description": "Consultoría", "quantity": 2, "price_unit": 50}
                ],
            },
        )

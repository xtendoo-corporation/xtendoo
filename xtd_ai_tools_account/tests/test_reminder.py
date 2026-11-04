from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestPaymentReminder(XtdAiAccountCase):
    """Wave 2B: payment reminder by email for an overdue invoice. It never
    posts or changes the invoice, and nothing in the agent posts an invoice."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer.email = "pagos@aging.example"

    def setUp(self):
        super().setUp()
        self.set_confirm(self.biller, False)
        self.run = self.start_run(self.biller)[0]
        self.overdue = self.make_move("out_invoice", self.customer, 100, "2026-01-15")

    def sc(self, args, name="send_payment_reminder"):
        return self.agent_call(self.biller, self.run, name, args, cids=self.company.ids)

    def test_reminder_card_shows_recipient_and_fixed_text(self):
        res = self.sc({"invoice": str(self.overdue.id)})
        self.assertEqual(res["status"], "pending_confirmation", res)
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        lines = {line["field"]: line["value"] for line in action.preview["lines"]}
        self.assertIn("pagos@aging.example", lines["Para"])
        self.assertIn(self.overdue.name, lines["Asunto"])
        self.assertIn("vencimiento", lines["Texto"])
        self.assertTrue(action.preview["irreversible"])
        write_date = self.overdue.write_date
        out = action.with_user(self.biller).action_confirm()
        self.assertEqual(out["state"], "confirmed", out)
        mail = self.env["mail.mail"].search(
            [("model", "=", "account.move"), ("res_id", "=", self.overdue.id)]
        )
        self.assertTrue(mail)
        self.assertIn(self.customer, mail.recipient_ids)
        self.assertEqual(self.overdue.state, "posted")
        self.assertEqual(self.overdue.write_date, write_date)

    def test_recent_reminder_not_resent(self):
        res = self.sc({"invoice": str(self.overdue.id)})
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        lines = {line["field"]: line["value"] for line in action.preview["lines"]}
        self.assertIn("Ninguno", lines["Recordatorios previos"])
        self.assertEqual(
            action.with_user(self.biller).action_confirm()["state"], "confirmed"
        )
        # Segundo intento dentro de la ventana: no hay tarjeta, se explica
        res = self.sc({"invoice": str(self.overdue.id)})
        self.assertEqual(res["error"]["code"], "validation", res)
        self.assertIn("recordatorio", res["error"]["message"])
        # Fuera de la ventana (ventana de 0 h = desactivada) vuelve a ofrecerse
        self.env["ir.config_parameter"].set_param(
            "xtd_ai.payment_reminder_window_hours", "0"
        )
        res = self.sc({"invoice": str(self.overdue.id)})
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_not_overdue_or_draft_refused(self):
        future = self.make_move("out_invoice", self.customer, 50, "2027-12-31")
        draft = self.make_move(
            "out_invoice", self.customer, 50, "2026-01-15", post=False
        )
        for invoice in (future, draft):
            res = self.sc({"invoice": str(invoice.id)})
            self.assertEqual(res["error"]["code"], "validation", res)
        self.assertEqual(draft.state, "draft")

    def test_no_free_recipient_or_text(self):
        res = self.sc({"invoice": str(self.overdue.id), "email": "otro@malo.example"})
        self.assertEqual(res["error"]["code"], "validation", res)
        res = self.sc({"invoice": str(self.overdue.id), "body": "Pague ya"})
        self.assertEqual(res["error"]["code"], "validation", res)

    def test_send_email_unlock_does_not_post_the_invoice(self):
        draft = self.make_move(
            "out_invoice", self.customer, 50, "2026-01-15", post=False
        )
        env = self.tool_env(self.biller, self.run, cids=self.company.ids)
        key = {
            "xtd_ai_grant": ("account.move.send_email",),
            "xtd_ai_unlock": ("account.move.send_email", draft.id),
        }
        move = env["account.move"].browse(draft.id).with_context(**key)
        with self.assertRaises(XtdAiDraftOnlyError):
            move.action_post()
        with self.assertRaises(XtdAiDraftOnlyError):
            move._post()
        self.assertEqual(draft.state, "draft")

    def test_no_tool_posts_an_invoice(self):
        tools = self.env["xtd.ai.toolbox"]._xtd_ai_tools()
        for name, tool in tools.items():
            self.assertNotIn("account.move.action_post", tool["unlocks"], name)
            self.assertNotIn("account.move._post", tool["unlocks"], name)
            self.assertNotIn("*.action_post", tool["unlocks"], name)

    def test_without_invoice_rights_not_offered(self):
        run = self.start_run(self.nobody)[0]
        _status, response = self.rpc(self.nobody, run, "tools/list", {})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertNotIn("send_payment_reminder", names)

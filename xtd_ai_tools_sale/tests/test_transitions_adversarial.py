from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import INJECTION, XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestTransitionsAdversarial(XtdAiSaleCase):
    """Wave 2B attacks: an email never leaves without a card, an unlock is
    never reused for another record or operation, external text brakes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.email = "alfa@cliente.example"

    def setUp(self):
        super().setUp()
        self.set_confirm(self.salesman, False)
        self.order = self.make_order()

    def test_email_is_never_below_a_card(self):
        Rule = self.env["xtd.ai.policy.rule"]
        Rule._xtd_ai_ensure_rows(self.company)
        for op_class in ("send_external", "confirm_sale"):
            row = Rule.search(
                [("company_id", "=", self.company.id), ("op_class", "=", op_class)]
            )
            with self.assertRaises(ValidationError):
                row.write({"level": "N1"})
        self.env["ir.config_parameter"].set_param(
            "xtd_ai.policy.level.send_external", "N1"
        )
        self.company.xtd_ai_profile = "agile"
        mails = self.env["mail.mail"].search_count([])
        res = self.sc(
            self.salesman, "send_quotation_email", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertEqual(self.env["mail.mail"].search_count([]), mails)
        self.assertEqual(self.order.state, "draft")

    def test_no_email_leaves_inside_a_run_without_its_unlock(self):
        run, _t = self.start_run(self.salesman)
        env = self.tool_env(self.salesman, run)
        order = env["sale.order"].browse(self.order.id)
        with self.assertRaises(XtdAiDraftOnlyError):
            order.message_post(
                body="Hola", message_type="comment", partner_ids=self.partner.ids
            )
        with self.assertRaises(XtdAiDraftOnlyError):
            order.action_quotation_send()
        # a grant of another tool does not open the email
        with self.assertRaises(XtdAiDraftOnlyError):
            order.with_context(
                xtd_ai_grant=("sale.order.action_confirm",),
                xtd_ai_unlock=("sale.order.send_email", order.id),
            ).message_post(
                body="Hola", message_type="comment", partner_ids=self.partner.ids
            )

    def test_preview_never_runs_unlocked(self):
        self.company.xtd_ai_profile = "agile"
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertEqual(self.order.state, "draft")
        res = self.sc(
            self.salesman, "send_quotation_email", {"order": str(self.order.id)}
        )
        self.assertEqual(self.order.state, "draft")
        self.assertFalse(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "sale.order"),
                    ("res_id", "=", self.order.id),
                    ("message_type", "=", "comment"),
                ]
            )
        )

    def test_attachment_with_orders_makes_every_transition_a_card(self):
        self.company.xtd_ai_profile = "agile"
        self.order.note = INJECTION
        attachment = self.upload(self.salesman)
        run, _t = self.start_run(
            self.salesman, text="Mira el pedido", attachment_ids=[attachment.id]
        )
        res = self.call(
            self.salesman,
            run,
            "cancel_sale_quotation",
            {"order": str(self.order.id)},
        )["structuredContent"]
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertEqual(self.order.state, "draft")

    def test_bulk_references_are_refused(self):
        other = self.make_order()
        self.company.xtd_ai_profile = "agile"
        for value in (f"{self.order.id},{other.id}", "*", "todos"):
            res = self.sc(self.salesman, "confirm_sale_order", {"order": value})
            self.assertEqual(res["status"], "error", (value, res))
        self.assertEqual((self.order | other).mapped("state"), ["draft", "draft"])

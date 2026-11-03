from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import INJECTION, XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleTransitions(XtdAiSaleCase):
    """Wave 2B: confirm, send by email and cancel a quotation (§4 Ventas)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.email = "alfa@cliente.example"

    def setUp(self):
        super().setUp()
        for user in (self.salesman, self.salesman2, self.sales_manager):
            self.set_confirm(user, False)
        self.order = self.make_order()

    def turn_on(self, op_class, level="N2"):
        self.set_policy(op_class, level)

    def confirm(self, user, result):
        self.assertEqual(result["status"], "pending_confirmation", result)
        action = self.env["xtd.ai.pending_action"].browse(result["pending_action_id"])
        out = action.with_user(user).action_confirm()
        return out, action

    def undo(self, user, action):
        return (
            self.env["xtd.ai.undo"]
            .with_user(user)
            ._xtd_ai_undo_edit(
                action.result_model,
                action.result_res_id,
                action.result_edit,
                since=action.create_date,
            )
        )

    def tool_names(self, user):
        run, _t = self.start_run(user)
        _status, response = self.rpc(user, run, "tools/list", {})
        return {t["name"] for t in response["result"]["tools"]}

    # -- confirm -----------------------------------------------------------
    def test_confirm_off_by_default_opens_the_quotation(self):
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "handoff", res)
        self.assertEqual(res["data"]["button"], "Confirmar")
        self.assertTrue(res["records"][0]["navigate"])
        self.assertEqual(self.order.state, "draft")
        self.assertFalse(
            self.env["xtd.ai.pending_action"].search_count(
                [("tool_name", "=", "confirm_sale_order")]
            )
        )

    def test_confirm_on_is_a_card_with_effects_and_undo(self):
        self.turn_on("confirm_sale")
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(self.order.state, "draft")
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        fields_ = [line["field"] for line in action.preview["lines"]]
        self.assertIn("Efecto", fields_)
        self.assertEqual(action.preview["confirm_label"], "Confirmar")
        self.assertTrue(
            any(
                "No escribe al cliente" in line["value"]
                for line in action.preview["lines"]
            )
        )
        out, action = self.confirm(self.salesman, res)
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.order.state, "sale")
        self.assertEqual(action.result_edit["transition"], "sale_confirm")
        self.assertIn("hecha «Confirmar presupuesto»", action._xtd_ai_confirmed_label())
        self.assertTrue(self.undo(self.salesman, action)["undone"])
        self.assertEqual(self.order.state, "draft")

    def test_agile_profile_is_a_card(self):
        self.company.xtd_ai_profile = "agile"
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_prudent_cannot_be_turned_on_below_floor(self):
        self.company.xtd_ai_profile = "prudent"
        self.turn_on("confirm_sale")
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_confirmed_order_is_refused(self):
        self.turn_on("confirm_sale")
        self.order.action_confirm()
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.assertEqual(res["error"]["code"], "validation", res)

    def test_high_discount_and_credit_shown_in_effects(self):
        self.turn_on("confirm_sale")
        self.order.order_line.discount = 30
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        self.assertTrue(
            any("30" in line["value"] for line in action.preview["lines"]),
            action.preview,
        )

    def test_unlock_is_for_one_order_and_one_operation(self):
        other = self.make_order()
        run, _t = self.start_run(self.salesman)
        env = self.tool_env(self.salesman, run)
        key = {
            "xtd_ai_grant": ("sale.order.action_confirm",),
            "xtd_ai_unlock": ("sale.order.action_confirm", self.order.id),
        }
        with self.assertRaises(XtdAiDraftOnlyError):
            env["sale.order"].browse(other.id).with_context(**key).action_confirm()
        with self.assertRaises(XtdAiDraftOnlyError):
            env["sale.order"].browse((self.order | other).ids).with_context(
                **key
            ).action_confirm()
        unlocked = env["sale.order"].browse(self.order.id).with_context(**key)
        for blocked in (
            unlocked.action_cancel,
            unlocked.unlink,
            unlocked.action_quotation_send,
        ):
            with self.assertRaises(XtdAiDraftOnlyError):
                blocked()
        # the confirm unlock does not let an email out
        with self.assertRaises(XtdAiDraftOnlyError):
            unlocked.message_post(
                body="x", message_type="comment", partner_ids=self.partner.ids
            )
        # without the grant of the running tool the key does nothing
        with self.assertRaises(XtdAiDraftOnlyError):
            env["sale.order"].browse(self.order.id).with_context(
                xtd_ai_unlock=("sale.order.action_confirm", self.order.id)
            ).action_confirm()
        self.assertEqual((self.order | other).mapped("state"), ["draft", "draft"])

    def test_note_with_orders_does_not_widen_the_card(self):
        self.turn_on("confirm_sale")
        self.order.note = INJECTION
        other = self.make_order()
        res = self.sc(
            self.salesman, "confirm_sale_order", {"order": str(self.order.id)}
        )
        self.confirm(self.salesman, res)
        self.assertEqual(self.order.state, "sale")
        self.assertEqual(other.state, "draft")

    def test_other_salesman_quotation_not_found(self):
        self.turn_on("confirm_sale")
        own2 = self.make_order(user=self.salesman2)
        res = self.sc(self.salesman, "confirm_sale_order", {"order": str(own2.id)})
        self.assertEqual(res["status"], "error", res)
        self.assertEqual(own2.state, "draft")

    def test_without_sales_rights_tools_not_offered(self):
        names = self.tool_names(self.nosales)
        self.assertFalse(
            {"confirm_sale_order", "send_quotation_email", "cancel_sale_quotation"}
            & names
        )
        self.assertIn("confirm_sale_order", self.tool_names(self.salesman))

    # -- send by email -------------------------------------------------------
    def test_send_quotation_email_card_shows_recipient_and_text(self):
        res = self.sc(
            self.salesman, "send_quotation_email", {"order": str(self.order.id)}
        )
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        lines = {line["field"]: line["value"] for line in action.preview["lines"]}
        self.assertIn("alfa@cliente.example", lines["Para"])
        self.assertTrue(lines["Asunto"])
        self.assertTrue(action.preview["irreversible"])
        self.assertEqual(self.order.state, "draft")
        mails = self.env["mail.mail"].search_count([])
        out, action = self.confirm(self.salesman, res)
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.order.state, "sent")
        sent = self.env["mail.mail"].search([], order="id desc", limit=5)
        self.assertGreater(self.env["mail.mail"].search_count([]), mails)
        self.assertIn(self.partner, sent.recipient_ids)
        # an email cannot be taken back: no "Deshacer"
        self.assertFalse(self.undo(self.salesman, action)["undone"])

    def test_send_has_no_recipient_argument(self):
        res = self.sc(
            self.salesman,
            "send_quotation_email",
            {"order": str(self.order.id), "email": "otro@malo.example"},
        )
        self.assertEqual(res["error"]["code"], "validation", res)

    def test_send_without_email_refused(self):
        order = self.make_order(partner=self.partner_b)
        res = self.sc(self.salesman, "send_quotation_email", {"order": str(order.id)})
        self.assertEqual(res["error"]["code"], "validation", res)

    def test_send_is_never_n1(self):
        self.company.xtd_ai_profile = "agile"
        res = self.sc(
            self.salesman, "send_quotation_email", {"order": str(self.order.id)}
        )
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_send_unlock_only_for_its_order(self):
        other = self.make_order()
        run, _t = self.start_run(self.salesman)
        env = self.tool_env(self.salesman, run)
        key = {
            "xtd_ai_grant": ("sale.order.send_email",),
            "xtd_ai_unlock": ("sale.order.send_email", self.order.id),
        }
        with self.assertRaises(XtdAiDraftOnlyError):
            env["sale.order"].browse(other.id).with_context(**key).message_post(
                body="x", message_type="comment", partner_ids=self.partner.ids
            )
        # a mail of another record is not let out by the unlock
        msg = other.message_post(body="interno")
        with self.assertRaises(XtdAiDraftOnlyError):
            env["mail.mail"].with_context(**key).create(
                {"mail_message_id": msg.id, "email_to": "x@y.example"}
            )
        with self.assertRaises(XtdAiDraftOnlyError):
            env["sale.order"].browse(self.order.id).with_context(**key).action_confirm()

    # -- cancel --------------------------------------------------------------
    def test_cancel_quotation_card_and_undo(self):
        res = self.sc(
            self.salesman, "cancel_sale_quotation", {"order": str(self.order.id)}
        )
        out, action = self.confirm(self.salesman, res)
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.order.state, "cancel")
        self.assertTrue(self.undo(self.salesman, action)["undone"])
        self.assertEqual(self.order.state, "draft")

    def test_cancel_confirmed_order_refused(self):
        self.order.action_confirm()
        res = self.sc(
            self.salesman, "cancel_sale_quotation", {"order": str(self.order.id)}
        )
        self.assertEqual(res["error"]["code"], "validation", res)
        self.assertEqual(self.order.state, "sale")

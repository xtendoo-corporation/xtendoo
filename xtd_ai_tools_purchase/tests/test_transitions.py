from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


@tagged("post_install", "-at_install")
class TestPurchaseTransitions(XtdAiCase):
    """Wave 2B: confirm and cancel an RFQ (§4 Compras), reinforced card above
    the purchase limit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = new_test_user(
            cls.env,
            "xtd_ai_buyer2b",
            groups=AI_GROUPS + ",purchase.group_purchase_user",
        )
        cls.nobody = new_test_user(cls.env, "xtd_ai_nobody2b", groups=AI_GROUPS)
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Proveedor Omega SL", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Tuerca Omega", "type": "consu", "standard_price": 1.0}
        )

    def setUp(self):
        super().setUp()
        self.set_confirm(self.buyer, False)
        self.company.xtd_ai_purchase_confirm_limit = 1000
        self.rfq = self.make_rfq(10, 2.0)

    def make_rfq(self, qty, price):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "price_unit": price,
                        }
                    )
                ],
            }
        )

    def sc(self, name, args, user=None):
        user = user or self.buyer
        runs = self.__dict__.setdefault("_runs", {})
        if user.id not in runs:
            runs[user.id] = self.start_run(user)[0]
        return self.call(user, runs[user.id], name, args)["structuredContent"]

    def turn_on(self):
        self.set_policy("confirm_purchase", "N2")

    def pending(self, res):
        self.assertEqual(res["status"], "pending_confirmation", res)
        return self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])

    def undo(self, action):
        return (
            self.env["xtd.ai.undo"]
            .with_user(self.buyer)
            ._xtd_ai_undo_edit(
                action.result_model,
                action.result_res_id,
                action.result_edit,
                since=action.create_date,
            )
        )

    def test_off_by_default_opens_the_rfq(self):
        res = self.sc("confirm_purchase_order", {"order": str(self.rfq.id)})
        self.assertEqual(res["status"], "handoff", res)
        self.assertEqual(self.rfq.state, "draft")

    def test_card_below_limit_and_undo(self):
        self.turn_on()
        action = self.pending(
            self.sc("confirm_purchase_order", {"order": str(self.rfq.id)})
        )
        self.assertFalse(action.preview.get("warning"))
        self.assertEqual(self.rfq.state, "draft")
        out = action.with_user(self.buyer).action_confirm()
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.rfq.state, "purchase")
        self.assertTrue(self.undo(action)["undone"])
        self.assertEqual(self.rfq.state, "draft")

    def test_reinforced_card_above_limit(self):
        self.turn_on()
        big = self.make_rfq(100, 20.0)
        action = self.pending(self.sc("confirm_purchase_order", {"order": str(big.id)}))
        warning = action.preview["warning"]
        self.assertIn("Proveedor Omega SL", warning)
        self.assertIn("2.420", warning.replace("2,420", "2.420"))
        self.assertIn("Proveedor Omega SL", action.preview["summary"])

    def test_unlock_only_its_order(self):
        other = self.make_rfq(1, 1.0)
        run, _t = self.start_run(self.buyer)
        env = self.tool_env(self.buyer, run)
        key = {
            "xtd_ai_grant": ("purchase.order.button_confirm",),
            "xtd_ai_unlock": ("purchase.order.button_confirm", self.rfq.id),
        }
        with self.assertRaises(XtdAiDraftOnlyError):
            env["purchase.order"].browse(other.id).with_context(**key).button_confirm()
        unlocked = env["purchase.order"].browse(self.rfq.id).with_context(**key)
        for blocked in (unlocked.button_cancel, unlocked.action_rfq_send):
            with self.assertRaises(XtdAiDraftOnlyError):
                blocked()
        self.assertEqual((self.rfq | other).mapped("state"), ["draft", "draft"])

    def test_cancel_rfq_and_undo(self):
        action = self.pending(
            self.sc("cancel_purchase_rfq", {"order": str(self.rfq.id)})
        )
        out = action.with_user(self.buyer).action_confirm()
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.rfq.state, "cancel")
        self.assertTrue(self.undo(action)["undone"])
        self.assertEqual(self.rfq.state, "draft")

    def test_confirmed_order_cannot_be_cancelled_by_the_agent(self):
        self.rfq.button_confirm()
        res = self.sc("cancel_purchase_rfq", {"order": str(self.rfq.id)})
        self.assertEqual(res["error"]["code"], "validation", res)

    def test_without_purchase_rights_not_offered(self):
        run, _t = self.start_run(self.nobody)
        _status, response = self.rpc(self.nobody, run, "tools/list", {})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertFalse({"confirm_purchase_order", "cancel_purchase_rfq"} & names)

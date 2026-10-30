from odoo.tests import tagged

from .test_purchase import TestPurchase as _Base


@tagged("post_install", "-at_install")
class TestPurchaseUndo(_Base):  # reuses the fixtures
    def test_rfq_draft_is_deleted_but_a_confirmed_order_is_not(self):
        self.set_confirm(self.buyer, False)
        res = self.tool(self.buyer, "create_purchase_rfq", self.rfq_args())
        order = self.env["purchase.order"].browse(res["data"]["id"])
        undo = self.env["xtd.ai.undo"].with_user(self.buyer)
        self.assertEqual(
            undo._xtd_ai_undo_state("purchase.order", order.id), "available"
        )
        self.assertEqual(
            undo._xtd_ai_undo("purchase.order", order.id),
            {"undone": True, "mode": "unlink"},
        )
        self.assertFalse(order.exists())
        res = self.tool(self.buyer, "create_purchase_rfq", self.rfq_args())
        order = self.env["purchase.order"].browse(res["data"]["id"])
        order.with_user(self.buyer).button_confirm()
        self.assertFalse(undo._xtd_ai_undo("purchase.order", order.id)["undone"])
        self.assertTrue(order.exists())

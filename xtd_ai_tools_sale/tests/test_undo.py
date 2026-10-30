from odoo.tests import tagged

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleUndo(XtdAiSaleCase):
    def undo(self, user, order, **kw):
        return (
            self.env["xtd.ai.undo"]
            .with_user(user)
            ._xtd_ai_undo(order._name, order.id, **kw)
        )

    def quote(self, user=None):
        user = user or self.salesman
        self.direct(user)
        res = self.sc(
            user,
            "create_sale_quotation",
            {
                "partner": str(self.partner.id),
                "lines": [{"product": str(self.product.id), "quantity": 3}],
            },
        )
        self.assertEqual(res["status"], "ok", res)
        return self.env["sale.order"].browse(res["records"][0]["id"])

    def test_manager_deletes_the_draft_quotation(self):
        order = self.quote(self.sales_manager)
        state = self.env["xtd.ai.undo"].with_user(self.sales_manager)
        self.assertEqual(state._xtd_ai_undo_state("sale.order", order.id), "available")
        self.assertEqual(self.undo(self.sales_manager, order)["mode"], "unlink")
        self.assertFalse(order.exists())

    def test_salesman_without_delete_right_cancels_it(self):
        order = self.quote()
        result = self.undo(self.salesman, order)
        self.assertEqual(result, {"undone": True, "mode": "cancel"})
        self.assertEqual(order.state, "cancel")  # never deleted with sudo
        undo = self.env["xtd.ai.undo"].with_user(self.salesman)
        self.assertEqual(undo._xtd_ai_undo_state("sale.order", order.id), "undone")

    def test_confirmed_or_invoiced_quotation_is_not_undoable(self):
        order = self.quote(self.sales_manager)
        order.with_user(self.sales_manager).action_confirm()
        result = self.undo(self.sales_manager, order)
        self.assertFalse(result["undone"], result)
        self.assertEqual(order.state, "sale")

    def test_added_lines_can_be_removed(self):
        order = self.quote()
        before = order.order_line
        res = self.sc(
            self.salesman,
            "add_sale_order_lines",
            {"order": order.name, "lines": [{"product": "Gadget XT", "quantity": 1}]},
        )
        ref = res["records"][0]
        new_lines = order.order_line - before
        self.assertEqual(ref["undo_lines"], new_lines.ids)
        undo = self.env["xtd.ai.undo"].with_user(self.salesman)
        self.assertEqual(
            undo._xtd_ai_undo_state("sale.order", order.id, line_ids=new_lines.ids),
            "available",
        )
        result = undo._xtd_ai_undo("sale.order", order.id, line_ids=new_lines.ids)
        self.assertEqual(result, {"undone": True, "mode": "unlink"})
        self.assertEqual(order.order_line, before)

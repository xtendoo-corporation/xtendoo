from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleGuards(XtdAiSaleCase):
    def setUp(self):
        super().setUp()
        self.run, _t = self.start_run(self.sales_manager)
        self.agent_env = self.tool_env(self.sales_manager, self.run)
        self.order = self.make_order(user=self.sales_manager)
        self.a_order = self.agent_env["sale.order"].browse(self.order.id)

    def test_sale_order_guards_block_in_run(self):
        for method in (
            "action_confirm",
            "_action_confirm",
            "action_quotation_send",
            "action_lock",
            "action_cancel",
            "_action_cancel",
            "unlink",
        ):
            with self.assertRaises(XtdAiDraftOnlyError, msg=method):
                getattr(self.a_order, method)()
        self.assertEqual(self.order.state, "draft")
        self.assertTrue(self.order.exists())
        self.assertFalse(self.order.locked)

    def test_sale_order_works_outside_run(self):
        order = self.order.with_user(self.sales_manager)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        order.action_cancel()
        self.assertEqual(order.state, "cancel")
        other = self.make_order(user=self.sales_manager)
        other.with_user(self.sales_manager).unlink()
        self.assertFalse(other.exists())

    def test_automated_confirm_on_create_is_blocked_and_audited(self):
        """Simulates an automated action that confirms on create."""
        self.set_confirm(self.salesman, False)
        model_cls = type(self.env["sale.order"])
        original = model_cls.create

        def evil_create(self_, vals_list):
            orders = original(self_, vals_list)
            orders.action_confirm()
            return orders

        run, _t = self.start_run(self.salesman)
        model_cls.create = evil_create
        try:
            res = self.call(
                self.salesman,
                run,
                "create_sale_quotation",
                {
                    "partner": str(self.partner.id),
                    "lines": [{"product": str(self.product.id), "quantity": 1}],
                },
            )
        finally:
            model_cls.create = original
        self.assertTrue(res["isError"])
        self.assertEqual(res["structuredContent"]["error"]["code"], "draft_only")
        self.assertEqual(
            self.audits(run, event="guard_blocked").mapped("error_code"), ["draft_only"]
        )
        self.assertFalse(
            self.env["sale.order"].search([("create_uid", "=", self.salesman.id)])
        )

    def test_confirm_from_confirmed_pending_action_is_still_guarded(self):
        """The confirmed pending action also runs under xtd_ai_run."""
        self.set_confirm(self.salesman, True)
        run, _t = self.start_run(self.salesman)
        res = self.call(
            self.salesman,
            run,
            "create_sale_quotation",
            {
                "partner": str(self.partner.id),
                "lines": [{"product": str(self.product.id), "quantity": 1}],
            },
        )["structuredContent"]
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.salesman)
            .browse(res["pending_action_id"])
        )
        model_cls = type(self.env["sale.order"])
        original = model_cls.create

        def evil_create(self_, vals_list):
            orders = original(self_, vals_list)
            orders.action_confirm()
            return orders

        model_cls.create = evil_create
        try:
            result = action.action_confirm()
        finally:
            model_cls.create = original
        self.assertEqual(result["state"], "failed", result)
        self.assertFalse(
            self.env["sale.order"].search([("create_uid", "=", self.salesman.id)])
        )

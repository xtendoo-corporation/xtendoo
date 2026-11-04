from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleDraftEdits(XtdAiSaleCase):
    """update_record on draft quotations and their lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_manager = new_test_user(
            cls.env,
            "xtd_sale_prod_mgr",
            groups=AI_GROUPS
            + ",sales_team.group_sale_manager,product.group_product_manager",
        )

    def changes(self, pairs):
        return [{"field": f, "value": v} for f, v in pairs]

    def create_product(self, pairs, user=None):
        return self.sc(
            user or self.direct(self.product_manager),
            "create_record",
            {"model": "product.template", "values": self.changes(pairs)},
        )

    def update(self, model, record, pairs, user=None):
        default = (
            self.product_manager if model == "product.template" else self.sales_manager
        )
        return self.sc(
            user or self.direct(default),
            "update_record",
            {"model": model, "record": str(record), "changes": self.changes(pairs)},
        )

    # -- draft quotations ---------------------------------------------------
    def test_edit_draft_quotation_and_lines(self):
        order = self.make_order(user=self.sales_manager)
        line = order.order_line
        result = self.update(
            "sale.order",
            order.id,
            [("client_order_ref", "PO-77"), ("validity_date", "2026-12-31")],
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(order.client_order_ref, "PO-77")
        result = self.update(
            "sale.order.line", line.id, [("product_uom_qty", "5"), ("discount", "10")]
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual((line.product_uom_qty, line.discount), (5.0, 10.0))
        # discount above the threshold (15 %), price and taxes: card
        for pairs in ([("discount", "20")], [("price_unit", "80")], [("tax_ids", "")]):
            self.assertEqual(
                self.update("sale.order.line", line.id, pairs)["status"],
                "pending_confirmation",
                pairs,
            )
        self.assertEqual(line.discount, 10.0)
        # the threshold of the company (the parameter is only the default of
        # new companies: every company keeps its own value, 0 included)
        self.company.xtd_ai_discount_threshold = 25
        self.assertEqual(
            self.update("sale.order.line", line.id, [("discount", "20")])["status"],
            "ok",
        )
        # product and customer are not editable
        for model, record, field in (
            ("sale.order.line", line.id, "product_id"),
            ("sale.order", order.id, "partner_id"),
            ("sale.order", order.id, "state"),
        ):
            self.assertEqual(
                self.update(model, record, [(field, "1")])["error"]["code"],
                "forbidden",
                field,
            )

    def test_confirmed_order_is_not_editable(self):
        order = self.make_order(user=self.sales_manager)
        order.action_confirm()
        for model, record in (
            ("sale.order", order.id),
            ("sale.order.line", order.order_line.id),
        ):
            result = self.update(model, record, [("client_order_ref", "x")])
            self.assertEqual(result["status"], "error", result)
        self.assertFalse(order.client_order_ref)

    def test_salesman_edits_only_his_own_quotations(self):
        mine = self.make_order(user=self.salesman)
        other = self.make_order(user=self.salesman2)
        user = self.direct(self.salesman)
        self.assertEqual(
            self.update("sale.order", mine.id, [("client_order_ref", "A")], user)[
                "status"
            ],
            "ok",
        )
        result = self.update("sale.order", other.id, [("client_order_ref", "B")], user)
        self.assertEqual(result["status"], "error")
        self.assertFalse(other.client_order_ref)

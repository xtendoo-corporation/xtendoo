from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase


@tagged("post_install", "-at_install")
class TestPurchaseDraftEdits(XtdAiCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = new_test_user(
            cls.env,
            "xtd_ai_rec_buyer",
            groups=AI_GROUPS + ",purchase.group_purchase_user",
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor Registro SL"})
        cls.product = cls.env["product.product"].create(
            {"name": "Tuerca Registro", "standard_price": 0.5}
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 10,
                            "price_unit": 2,
                        }
                    )
                ],
            }
        )

    def update(self, model, record, pairs):
        self.set_confirm(self.buyer, False)
        runs = self.__dict__.setdefault("_runs", {})
        if "r" not in runs:
            runs["r"] = self.start_run(self.buyer)[0]
        run = runs["r"]
        return self.call(
            self.buyer,
            run,
            "update_record",
            {
                "model": model,
                "record": str(record),
                "changes": [{"field": f, "value": v} for f, v in pairs],
            },
        )["structuredContent"]

    def test_edit_rfq_and_lines(self):
        line = self.order.order_line
        result = self.update(
            "purchase.order",
            self.order.id,
            [("partner_ref", "OF-123"), ("date_planned", "2026-11-15")],
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(self.order.partner_ref, "OF-123")
        result = self.update(
            "purchase.order.line", line.id, [("product_qty", "12"), ("name", "Tuercas")]
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual((line.product_qty, line.name), (12.0, "Tuercas"))
        for pairs in ([("price_unit", "1.5")], [("discount", "30")]):
            self.assertEqual(
                self.update("purchase.order.line", line.id, pairs)["status"],
                "pending_confirmation",
            )
        self.assertEqual(line.price_unit, 2.0)

    def test_confirmed_order_and_forbidden_fields(self):
        for field in ("partner_id", "state", "company_id", "payment_term_id"):
            result = self.update("purchase.order", self.order.id, [(field, "1")])
            self.assertEqual(result["error"]["code"], "forbidden", field)
        self.order.button_confirm()
        result = self.update("purchase.order", self.order.id, [("partner_ref", "X")])
        self.assertEqual(result["status"], "error")
        self.assertFalse(self.order.partner_ref)

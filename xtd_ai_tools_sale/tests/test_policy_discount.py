from odoo.tests import tagged

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleDiscountPolicy(XtdAiSaleCase):
    """H1: the discount threshold applies when creating lines, not only when
    editing them; 0 is a real threshold; with several companies the threshold,
    profile and pause are those of the order's company (risks 3 and 4)."""

    def setUp(self):
        super().setUp()
        self.direct(self.salesman)
        self.direct(self.multi_user)
        (self.company | self.company2).write(
            {
                "xtd_ai_discount_threshold": 15.0,
                "xtd_ai_profile": "balanced",
                "xtd_ai_paused": False,
            }
        )
        self.both = [self.company.id, self.company2.id]

    def lines(self, *discounts):
        rows = []
        for discount in discounts:
            row = {"product": str(self.product.id), "quantity": 2}
            if discount is not None:
                row["discount"] = discount
            rows.append(row)
        return rows

    def quote(self, *discounts, user=None, **kw):
        args = {"partner": str(self.partner.id), "lines": self.lines(*discounts)}
        if "company" in kw:
            args["company"] = str(kw.pop("company").id)
        return self.sc(user or self.salesman, "create_sale_quotation", args, **kw)

    def add(self, order, *discounts, user=None, **kw):
        return self.sc(
            user or self.salesman,
            "add_sale_order_lines",
            {"order": str(order.id), "lines": self.lines(*discounts)},
            **kw,
        )

    def count(self):
        return self.env["sale.order"].search_count([])

    def confirm(self, user, res):
        self.assertEqual(res["status"], "pending_confirmation", res)
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        return action.with_user(user).action_confirm()

    # ------------------------------------------------------------------
    # Creating lines (H1)
    # ------------------------------------------------------------------
    def test_create_up_to_the_threshold_is_done(self):
        for discounts in ((None,), (0,), (15,), (5, 15)):
            res = self.quote(*discounts)
            self.assertEqual(res["status"], "ok", (discounts, res))

    def test_create_above_the_threshold_asks_for_a_card(self):
        before = self.count()
        for discounts in ((15.5,), (5, 40), (100,)):
            res = self.quote(*discounts)
            self.assertEqual(res["status"], "pending_confirmation", (discounts, res))
        self.assertEqual(self.count(), before)  # nothing written

    def test_full_discount_only_through_the_card(self):
        """E13/F1: «2 taladros con un 100 % de descuento» is a card; once the
        user accepts it the draft is created as asked."""
        before = self.count()
        out = self.confirm(self.salesman, self.quote(100))
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(self.count(), before + 1)
        order = self.env["sale.order"].search([], order="id desc", limit=1)
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.order_line.discount, 100)
        self.assertEqual(order.amount_untaxed, 0)

    def test_add_lines_above_the_threshold_asks_for_a_card(self):
        order = self.make_order()
        lines = len(order.order_line)
        self.assertEqual(self.add(order, 10)["status"], "ok")
        res = self.add(order, 50)
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertEqual(len(order.order_line), lines + 1)
        res = self.add(order, None, 100)
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_zero_threshold_means_any_discount(self):
        """Risk 4: 0 is a value, not «empty, use the 15 %»."""
        self.company.xtd_ai_discount_threshold = 0
        self.assertEqual(self.company.xtd_ai_discount_threshold, 0)
        self.assertEqual(self.quote(None)["status"], "ok")
        self.assertEqual(self.quote(0)["status"], "ok")
        res = self.quote(0.5)
        self.assertEqual(res["status"], "pending_confirmation", res)
        res = self.add(self.make_order(), 1)
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_edit_and_create_follow_the_same_threshold(self):
        self.company.xtd_ai_discount_threshold = 30
        order = self.make_order()
        line = order.order_line[:1]
        res = self.sc(
            self.salesman,
            "update_record",
            {
                "model": "sale.order.line",
                "record": str(line.id),
                "changes": [{"field": "discount", "value": "25"}],
            },
        )
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(self.quote(25)["status"], "ok")
        self.assertEqual(self.quote(35)["status"], "pending_confirmation")

    # ------------------------------------------------------------------
    # Company of the document (risk 3)
    # ------------------------------------------------------------------
    def test_threshold_of_the_company_of_the_order(self):
        self.company.xtd_ai_discount_threshold = 10
        self.company2.xtd_ai_discount_threshold = 50
        # the context company (first active) is self.company; the quotation
        # goes to company2, whose threshold rules
        res = self.quote(
            30, user=self.multi_user, company=self.company2, cids=self.both
        )
        self.assertEqual(res["status"], "ok", res)
        order = self.env["sale.order"].browse(res["data"]["id"])
        self.assertEqual(order.company_id, self.company2)
        res = self.quote(30, user=self.multi_user, company=self.company, cids=self.both)
        self.assertEqual(res["status"], "pending_confirmation", res)
        res = self.add(order, 30, user=self.multi_user, cids=self.both)
        self.assertEqual(res["status"], "ok", res)
        self.company2.xtd_ai_discount_threshold = 20
        res = self.add(order, 30, user=self.multi_user, cids=self.both)
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_profile_of_the_company_of_the_order(self):
        self.company2.xtd_ai_profile = "prudent"
        res = self.quote(
            None, user=self.multi_user, company=self.company2, cids=self.both
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        res = self.quote(
            None, user=self.multi_user, company=self.company, cids=self.both
        )
        self.assertEqual(res["status"], "ok", res)
        # the other way round: a prudent context company does not rule a
        # document of a balanced one
        self.company.xtd_ai_profile = "prudent"
        self.company2.xtd_ai_profile = "balanced"
        order2 = self.make_order(user=self.multi_user, company=self.company2)
        res = self.add(order2, None, user=self.multi_user, cids=self.both)
        self.assertEqual(res["status"], "ok", res)
        res = self.quote(None, user=self.multi_user, cids=self.both)
        self.assertEqual(res["status"], "pending_confirmation", res)

    def test_pause_of_the_company_of_the_order(self):
        order2 = self.make_order(user=self.multi_user, company=self.company2)
        self.company2.xtd_ai_paused = True
        res = self.add(order2, None, user=self.multi_user, cids=self.both)
        self.assertEqual(res["error"]["code"], "paused", res)
        res = self.quote(
            None, user=self.multi_user, company=self.company2, cids=self.both
        )
        self.assertEqual(res["error"]["code"], "paused", res)
        res = self.quote(None, user=self.multi_user, cids=self.both)
        self.assertEqual(res["status"], "ok", res)

    def test_order_of_a_company_not_active_in_the_run(self):
        order2 = self.make_order(user=self.multi_user, company=self.company2)
        res = self.add(order2, None, user=self.multi_user, cids=[self.company.id])
        self.assertEqual(res["status"], "error", res)
        self.assertEqual(len(order2.order_line), 1)

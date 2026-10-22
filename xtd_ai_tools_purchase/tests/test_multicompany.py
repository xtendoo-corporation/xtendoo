import json

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase


@tagged("post_install", "-at_install")
class TestPurchaseMultiCompany(XtdAiCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.company2.name = "AI Norte SL"
        cls.company3 = env["res.company"].create({"name": "AI forbidden company"})
        cls.cids = [cls.company.id, cls.company2.id]
        cls.user_mc = new_test_user(
            env,
            "xtd_ai_mc_user",
            groups=AI_GROUPS + ",purchase.group_purchase_user",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.cids)],
        )
        cls.vendor = env["res.partner"].create(
            {"name": "Proveedor MC SL", "supplier_rank": 1}
        )
        cls.product = env["product.product"].create(
            {
                "name": "Tornillo MC",
                "default_code": "MC-1",
                "type": "consu",
                "list_price": 1.0,
                "standard_price": 0.5,
            }
        )
        cls.po1 = cls.make_po(cls.company, 10, 2.0)
        cls.po2 = cls.make_po(cls.company2, 1, 7.0)
        cls.po3 = cls.make_po(cls.company3, 3, 9.0)
        for po in cls.po1 | cls.po2 | cls.po3:
            po.button_confirm()
        env.flush_all()

    @classmethod
    def make_po(cls, company, qty, price):
        return (
            cls.env["purchase.order"]
            .with_company(company)
            .create(
                {
                    "partner_id": cls.vendor.id,
                    "company_id": company.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": cls.product.id,
                                "product_qty": qty,
                                "price_unit": price,
                            }
                        )
                    ],
                }
            )
        )

    def mc(self, name, args=None, cids=None):
        run = getattr(self, "_mc_run", None) or self.start_run(self.user_mc)[0]
        self._mc_run = run
        return self.call(self.user_mc, run, name, args or {}, cids=cids or self.cids)[
            "structuredContent"
        ]

    # ------------------------------------------------------------------
    def test_orders_labelled_and_filtered(self):
        rows = {
            r["id"]: r
            for r in self.mc("search_purchase_orders", {"vendor": "MC"})["data"][
                "items"
            ]
        }
        self.assertEqual(set(rows), {self.po1.id, self.po2.id})
        self.assertEqual(rows[self.po1.id]["company"], self.company.name)
        self.assertEqual(rows[self.po2.id]["company"], "AI Norte SL")
        for value in (str(self.company2.id), "AI Norte SL", "norte"):
            res = self.mc("search_purchase_orders", {"vendor": "MC", "company": value})
            self.assertEqual(
                {r["id"] for r in res["data"]["items"]}, {self.po2.id}, value
            )
        res = self.mc(
            "get_purchase_order", {"name": self.po2.name, "company": "AI Norte SL"}
        )
        self.assertEqual(res["data"]["company"], "AI Norte SL")
        res = self.mc(
            "get_purchase_order", {"name": self.po2.name, "company": self.company.name}
        )
        self.assertEqual(res["error"]["code"], "not_found")

    def test_single_company_has_no_label(self):
        res = self.mc(
            "search_purchase_orders", {"vendor": "MC"}, cids=[self.company.id]
        )
        self.assertEqual([r["id"] for r in res["data"]["items"]], [self.po1.id])
        self.assertNotIn("company", res["data"]["items"][0])
        res = self.mc(
            "search_purchase_orders",
            {"company": self.company2.name},
            cids=[self.company.id],
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertIn(self.company.name, res["error"]["message"])

    def test_not_active_company_is_not_found(self):
        args = {
            "search_purchase_orders": {},
            "purchase_report": {"group_by": "vendor"},
        }
        for tool, extra in args.items():
            for value in (self.company3.name, str(self.company3.id)):
                res = self.mc(tool, extra | {"company": value})
                self.assertEqual(res["error"]["code"], "not_found", tool)
                dumped = json.dumps(res)
                self.assertNotIn(self.po3.name, dumped)
                self.assertNotIn("data", res)

    def test_purchase_report_split(self):
        self.env.flush_all()
        res = self.mc("purchase_report", {"group_by": "vendor", "limit": 200})
        rows = [
            r
            for r in res["data"]["items"]
            if r["vendor"] and r["vendor"]["id"] == self.vendor.id
        ]
        self.assertEqual(
            {r["company"]: r["untaxed_total"]["amount"] for r in rows},
            {self.company.name: 20.0, "AI Norte SL": 7.0},
        )
        res = self.mc(
            "purchase_report", {"group_by": "vendor", "company": "AI Norte SL"}
        )
        rows = [
            r
            for r in res["data"]["items"]
            if r["vendor"] and r["vendor"]["id"] == self.vendor.id
        ]
        self.assertEqual([r["untaxed_total"]["amount"] for r in rows], [7.0])
        self.assertNotIn("company", rows[0])
        res = self.mc("purchase_report", {"group_by": "vendor"}, cids=[self.company.id])
        self.assertTrue(all("company" not in r for r in res["data"]["items"]))

    def test_rfq_created_in_requested_company(self):
        self.set_confirm(self.user_mc, False)
        args = {
            "vendor": str(self.vendor.id),
            "lines": [{"product": "MC-1", "quantity": 2}],
        }
        res = self.mc("create_purchase_rfq", args | {"company": "AI Norte SL"})
        self.assertEqual(res["status"], "ok", res)
        order = self.env["purchase.order"].browse(res["records"][0]["id"])
        self.assertEqual((order.company_id, order.state), (self.company2, "draft"))
        self.assertEqual(res["data"]["company"], "AI Norte SL")
        res = self.mc("create_purchase_rfq", args)
        self.assertEqual(
            self.env["purchase.order"].browse(res["records"][0]["id"]).company_id,
            self.company,
        )
        before = self.env["purchase.order"].search_count([])
        res = self.mc("create_purchase_rfq", args | {"company": self.company3.name})
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(self.env["purchase.order"].search_count([]), before)
        res = self.mc(
            "create_purchase_rfq",
            args | {"company": "AI Norte SL"},
            cids=[self.company.id],
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(self.env["purchase.order"].search_count([]), before)

    def test_rfq_preview_shows_company(self):
        self.set_confirm(self.user_mc, True)
        res = self.mc(
            "create_purchase_rfq",
            {
                "vendor": str(self.vendor.id),
                "company": "AI Norte SL",
                "lines": [{"product": "MC-1", "quantity": 2}],
            },
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn("AI Norte SL", res["summary"])

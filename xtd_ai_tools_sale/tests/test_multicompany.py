import json

from odoo import Command, fields
from odoo.tests import tagged

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestSaleMultiCompany(XtdAiSaleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.company3 = env["res.company"].create({"name": "AI forbidden company"})
        cls.company2.name = "AI Norte SL"
        cls.both = [cls.company.id, cls.company2.id]
        cls.o1 = cls.make_order_mc(cls.company, 1.0)
        cls.o2 = cls.make_order_mc(cls.company2, 5.0)
        cls.o3 = cls.make_order_mc(cls.company3, 9.0)
        (cls.o1 | cls.o2 | cls.o3).action_confirm()
        cls.l1 = cls.make_lead("MC Opp Uno", cls.company, 1000)
        cls.l2 = cls.make_lead("MC Opp Dos", cls.company2, 2000)
        cls.l3 = cls.make_lead("MC Opp Tres", cls.company3, 3000)
        env.flush_all()

    @classmethod
    def make_order_mc(cls, company, qty):
        return (
            cls.env["sale.order"]
            .with_company(company)
            .create(
                {
                    "partner_id": cls.partner.id,
                    "user_id": cls.multi_user.id,
                    "company_id": company.id,
                    "order_line": [
                        Command.create(
                            {"product_id": cls.product.id, "product_uom_qty": qty}
                        )
                    ],
                }
            )
        )

    @classmethod
    def make_lead(cls, name, company, revenue):
        return (
            cls.env["crm.lead"]
            .with_company(company)
            .create(
                {
                    "name": name,
                    "type": "opportunity",
                    "user_id": cls.multi_user.id
                    if company in cls.multi_user.company_ids
                    else False,
                    "company_id": company.id,
                    "expected_revenue": revenue,
                }
            )
        )

    def call_mc(self, name, args=None, cids=None):
        return self.sc(self.multi_user, name, args or {}, cids=cids or self.both)

    def test_orders_labelled_with_company(self):
        res = self.call_mc("search_sale_orders")
        by_name = {r["name"]: r for r in res["data"]["items"]}
        self.assertEqual(by_name[self.o1.name]["company"], self.company.name)
        self.assertEqual(by_name[self.o2.name]["company"], "AI Norte SL")
        self.assertNotIn(self.o3.name, by_name)

    def test_single_company_has_no_label(self):
        res = self.call_mc("search_sale_orders", cids=[self.company.id])
        self.assertTrue(res["data"]["items"])
        for row in res["data"]["items"]:
            self.assertNotIn("company", row)
        res = self.call_mc("search_opportunities", cids=[self.company.id])
        for row in res["data"]["items"]:
            self.assertNotIn("company", row)

    def test_company_filter_by_id_and_name(self):
        for value in (str(self.company2.id), "AI Norte SL", "norte"):
            res = self.call_mc("search_sale_orders", {"company": value})
            self.assertEqual(
                {r["name"] for r in res["data"]["items"]}
                & {self.o1.name, self.o2.name},
                {self.o2.name},
                value,
            )
            res = self.call_mc("search_opportunities", {"company": value})
            names = {r["name"]["untrusted_text"] for r in res["data"]["items"]}
            self.assertIn("MC Opp Dos", names)
            self.assertNotIn("MC Opp Uno", names)
        res = self.call_mc(
            "get_sale_order", {"order": self.o2.name, "company": "AI Norte SL"}
        )
        self.assertEqual(res["data"]["company"], "AI Norte SL")
        res = self.call_mc(
            "get_sale_order", {"order": self.o2.name, "company": self.company.name}
        )
        self.assertEqual(res["error"]["code"], "not_found")

    def test_inactive_or_forbidden_company_is_not_found(self):
        for target in (self.company3, self.company2):
            cids = [self.company.id] if target == self.company2 else self.both
            for tool in (
                "search_sale_orders",
                "search_opportunities",
                "sales_report",
                "pipeline_report",
            ):
                args = {"company": target.name}
                if tool == "sales_report":
                    args.update(
                        group_by="customer",
                        date_from="2000-01-01",
                        date_to="2100-01-01",
                    )
                res = self.call_mc(tool, args, cids=cids)
                self.assertEqual(res["error"]["code"], "not_found", tool)
                self.assertIn(self.company.name, res["error"]["message"])
                dumped = json.dumps(res)
                self.assertNotIn(self.o3.name, dumped)
                self.assertNotIn("MC Opp Tres", dumped)
            res = self.call_mc(
                "search_sale_orders", {"company": str(target.id)}, cids=cids
            )
            self.assertEqual(res["error"]["code"], "not_found")

    def test_sales_report_split_by_company(self):
        today = str(fields.Date.today())
        args = {"group_by": "customer", "date_from": today, "date_to": today}
        data = self.call_mc("sales_report", args)["data"]
        self.assertNotIn("total_amount_untaxed", data)
        totals = {
            t["company"]: t["total_amount_untaxed"]["amount"]
            for t in data["totals_by_company"]
        }
        self.assertEqual(totals, {self.company.name: 100.0, "AI Norte SL": 500.0})
        self.assertEqual({r["company"] for r in data["items"]}, set(totals))
        data = self.call_mc("sales_report", args | {"company": "AI Norte SL"})["data"]
        self.assertEqual(data["total_amount_untaxed"]["amount"], 500.0)
        self.assertNotIn("totals_by_company", data)

    def test_pipeline_report_split_by_company(self):
        data = self.call_mc("pipeline_report", {"group_by": "salesperson"})["data"]
        totals = {
            t["company"]: t["total_expected_revenue"]["amount"]
            for t in data["totals_by_company"]
        }
        self.assertEqual(totals.get(self.company.name), 1000.0)
        self.assertEqual(totals.get("AI Norte SL"), 2000.0)
        self.assertNotIn(self.company3.name, totals)
        self.assertNotIn("total_count", data)
        data = self.call_mc("pipeline_report", {"company": str(self.company2.id)})[
            "data"
        ]
        self.assertEqual(data["total_expected_revenue"]["amount"], 2000.0)

    def test_quotation_created_in_requested_company(self):
        self.direct(self.multi_user)
        args = {
            "partner": str(self.partner.id),
            "lines": [{"product": str(self.product.id), "quantity": 2}],
        }
        res = self.call_mc("create_sale_quotation", args | {"company": "AI Norte SL"})
        self.assertEqual(res["status"], "ok", res)
        order = self.env["sale.order"].browse(res["records"][0]["id"])
        self.assertEqual(order.company_id, self.company2)
        self.assertEqual(res["data"]["company"], "AI Norte SL")
        # default: first active company
        res = self.call_mc(
            "create_sale_quotation", args, cids=[self.company2.id, self.company.id]
        )
        order = self.env["sale.order"].browse(res["records"][0]["id"])
        self.assertEqual(order.company_id, self.company2)
        res = self.call_mc("create_sale_quotation", args)
        self.assertEqual(
            self.env["sale.order"].browse(res["records"][0]["id"]).company_id,
            self.company,
        )
        # not active: refused, nothing created
        before = self.env["sale.order"].search_count([])
        res = self.call_mc(
            "create_sale_quotation", args | {"company": self.company3.name}
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(self.env["sale.order"].search_count([]), before)

    def test_quotation_preview_shows_company(self):
        self.set_confirm(self.multi_user, True)
        res = self.call_mc(
            "create_sale_quotation",
            {
                "partner": str(self.partner.id),
                "company": "AI Norte SL",
                "lines": [{"product": str(self.product.id), "quantity": 2}],
            },
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn("AI Norte SL", res["summary"])

    def test_opportunity_created_in_requested_company(self):
        self.direct(self.multi_user)
        res = self.call_mc(
            "create_opportunity",
            {"name": "MC nueva opp", "company": str(self.company2.id)},
        )
        self.assertEqual(res["status"], "ok", res)
        lead = self.env["crm.lead"].browse(res["records"][0]["id"])
        self.assertEqual(lead.company_id, self.company2)
        self.assertEqual(res["data"]["company"], "AI Norte SL")
        res = self.call_mc(
            "create_opportunity", {"name": "MC otra opp", "company": self.company3.name}
        )
        self.assertEqual(res["error"]["code"], "not_found")
        # single active company: only that one is accepted
        res = self.call_mc(
            "create_opportunity",
            {"name": "MC una opp", "company": "AI Norte SL"},
            cids=[self.company.id],
        )
        self.assertEqual(res["error"]["code"], "not_found")

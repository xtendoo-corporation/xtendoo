import json

from odoo.tests import tagged

from .common import XtdAiCrmCase


@tagged("post_install", "-at_install")
class TestCrmMultiCompany(XtdAiCrmCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.company3 = env["res.company"].create({"name": "AI forbidden company"})
        cls.company2.name = "AI Norte SL"
        cls.both = [cls.company.id, cls.company2.id]
        cls.l1 = cls.make_lead("MC Opp Uno", cls.company, 1000)
        cls.l2 = cls.make_lead("MC Opp Dos", cls.company2, 2000)
        cls.l3 = cls.make_lead("MC Opp Tres", cls.company3, 3000)
        env.flush_all()

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

    def test_opportunities_labelled_with_company(self):
        res = self.call_mc("search_opportunities")
        rows = {r["name"]["untrusted_text"]: r for r in res["data"]["items"]}
        self.assertEqual(rows["MC Opp Uno"]["company"], self.company.name)
        self.assertEqual(rows["MC Opp Dos"]["company"], "AI Norte SL")
        self.assertNotIn("MC Opp Tres", rows)

    def test_single_company_has_no_label(self):
        res = self.call_mc("search_opportunities", cids=[self.company.id])
        self.assertTrue(res["data"]["items"])
        for row in res["data"]["items"]:
            self.assertNotIn("company", row)

    def test_company_filter_by_id_and_name(self):
        for value in (str(self.company2.id), "AI Norte SL", "norte"):
            res = self.call_mc("search_opportunities", {"company": value})
            names = {r["name"]["untrusted_text"] for r in res["data"]["items"]}
            self.assertIn("MC Opp Dos", names)
            self.assertNotIn("MC Opp Uno", names)

    def test_inactive_or_forbidden_company_is_not_found(self):
        for target in (self.company3, self.company2):
            cids = [self.company.id] if target == self.company2 else self.both
            for tool in ("search_opportunities", "pipeline_report"):
                res = self.call_mc(tool, {"company": target.name}, cids=cids)
                self.assertEqual(res["error"]["code"], "not_found", tool)
                self.assertIn(self.company.name, res["error"]["message"])
                self.assertNotIn("MC Opp Tres", json.dumps(res))
            res = self.call_mc(
                "search_opportunities", {"company": str(target.id)}, cids=cids
            )
            self.assertEqual(res["error"]["code"], "not_found")

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

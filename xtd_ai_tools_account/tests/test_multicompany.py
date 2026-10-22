import json

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestAccountMultiCompany(XtdAiAccountCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company3 = cls._new_company("AI accounting company 3")
        cls.both = [cls.company.id, cls.company2.id]
        cls.multi = new_test_user(
            cls.env,
            "xtd_ai_acc_multi",
            groups=AI_GROUPS + ",account.group_account_invoice",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.both)],
        )
        cls.m1 = cls.make_move_mc("out_invoice", 100, cls.company)
        cls.m2 = cls.make_move_mc("out_invoice", 77, cls.company2)
        cls.m3 = cls.make_move_mc("out_invoice", 55, cls.company3)
        cls.env.flush_all()

    @classmethod
    def make_move_mc(cls, move_type, amount, company):
        move = (
            cls.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": move_type,
                    "partner_id": cls.customer.id,
                    "invoice_date": "2026-01-01",
                    "invoice_date_due": "2026-06-01",
                    "invoice_payment_term_id": False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Servicio",
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": [Command.set([])],
                            }
                        )
                    ],
                }
            )
        )
        move.action_post()
        return move

    def mc(self, name, args=None, cids=None):
        run = self.__dict__.setdefault("_mc_run", None) or self.start_run(self.multi)[0]
        self._mc_run = run
        return self.agent_call(
            self.multi, run, name, args or {}, cids=cids or self.both
        )

    def test_invoices_labelled_and_filtered(self):
        rows = {r["id"]: r for r in self.mc("search_invoices")["data"]["items"]}
        self.assertEqual(
            set(rows) & {self.m1.id, self.m2.id, self.m3.id}, {self.m1.id, self.m2.id}
        )
        self.assertEqual(rows[self.m1.id]["company"], self.company.name)
        self.assertEqual(rows[self.m2.id]["company"], self.company2.name)
        for value in (str(self.company2.id), self.company2.name, "company 2"):
            rows = self.mc("search_invoices", {"company": value})["data"]["items"]
            self.assertEqual({r["id"] for r in rows}, {self.m2.id}, value)
        res = self.mc(
            "get_invoice", {"invoice_id": self.m2.id, "company": self.company.name}
        )
        self.assertEqual(res["error"]["code"], "not_found")

    def test_single_company_has_no_label(self):
        rows = self.mc("search_invoices", cids=[self.company.id])["data"]["items"]
        self.assertEqual({r["id"] for r in rows}, {self.m1.id})
        self.assertNotIn("company", rows[0])
        res = self.mc(
            "search_invoices", {"company": self.company2.name}, cids=[self.company.id]
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertIn(self.company.name, res["error"]["message"])
        self.assertNotIn(str(self.m2.name), json.dumps(res))

    def test_not_active_company_is_not_found(self):
        for tool, args in (
            ("search_invoices", {}),
            ("receivables_payables_summary", {"kind": "receivable"}),
        ):
            res = self.mc(tool, args | {"company": self.company3.name})
            self.assertEqual(res["error"]["code"], "not_found", tool)
            self.assertNotIn("55", json.dumps(res["error"]))
            res = self.mc(tool, args | {"company": str(self.company3.id)})
            self.assertEqual(res["error"]["code"], "not_found", tool)

    def test_summary_split_per_company(self):
        with self.at_today():
            data = self.mc("receivables_payables_summary", {"kind": "receivable"})[
                "data"
            ]
            totals = {t["company"]: t["total"]["amount"] for t in data["totals"]}
            self.assertEqual(
                totals, {self.company.name: 100.0, self.company2.name: 77.0}
            )
            self.assertEqual(
                {r["company"] for r in data["partners"]["items"]}, set(totals)
            )
            data = self.mc(
                "receivables_payables_summary",
                {"kind": "receivable", "company": self.company2.name},
            )["data"]
            self.assertEqual([t["total"]["amount"] for t in data["totals"]], [77.0])
            data = self.mc(
                "receivables_payables_summary",
                {"kind": "receivable"},
                cids=[self.company.id],
            )["data"]
            self.assertNotIn("company", data["partners"]["items"][0])

    def test_invoice_created_in_requested_company(self):
        self.set_confirm(self.multi, False)
        args = {
            "partner_id": self.customer.id,
            "lines": [{"description": "x", "quantity": 1, "price_unit": 5}],
        }
        res = self.mc("create_customer_invoice", args | {"company": self.company2.name})
        self.assertEqual(res["status"], "ok", res)
        move = self.env["account.move"].browse(res["records"][0]["id"])
        self.assertEqual(
            (move.company_id, move.journal_id.company_id),
            (self.company2, self.company2),
        )
        self.assertEqual(res["data"]["company"], self.company2.name)
        bill = args | {"ref": "F-MC-1", "invoice_date": "2026-03-01"}
        res = self.mc("create_vendor_bill", bill | {"company": str(self.company.id)})
        move = self.env["account.move"].browse(res["records"][0]["id"])
        self.assertEqual(move.company_id, self.company)
        # default: first active company
        res = self.mc(
            "create_customer_invoice", args, cids=[self.company2.id, self.company.id]
        )
        self.assertEqual(
            self.env["account.move"].browse(res["records"][0]["id"]).company_id,
            self.company2,
        )
        before = self.env["account.move"].search_count([])
        res = self.mc("create_customer_invoice", args | {"company": self.company3.name})
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(self.env["account.move"].search_count([]), before)
        res = self.mc(
            "create_vendor_bill",
            bill | {"company": self.company2.name},
            cids=[self.company.id],
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(self.env["account.move"].search_count([]), before)

    def test_preview_shows_company(self):
        self.set_confirm(self.multi, True)
        res = self.mc(
            "create_customer_invoice",
            {
                "partner_id": self.customer.id,
                "company": self.company2.name,
                "lines": [{"description": "x", "quantity": 1, "price_unit": 5}],
            },
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn(self.company2.name, res["summary"])

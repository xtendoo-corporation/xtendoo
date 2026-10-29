from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase

TODAY = date(2026, 6, 30)


class XtdAiAccountCase(XtdAiCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Fresh companies: the demo data already holds invoices in the main company.
        cls.company = cls._new_company("AI accounting company 1")
        cls.company2 = cls._new_company("AI accounting company 2")
        cls.biller = new_test_user(
            cls.env,
            "xtd_ai_biller",
            groups=AI_GROUPS + ",account.group_account_invoice",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        cls.reader = new_test_user(
            cls.env,
            "xtd_ai_acc_reader",
            groups=AI_GROUPS + ",account.group_account_readonly",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        cls.nobody = new_test_user(
            cls.env,
            "xtd_ai_acc_none",
            groups=AI_GROUPS,
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        cls.biller2 = new_test_user(
            cls.env,
            "xtd_ai_biller2",
            groups=AI_GROUPS + ",account.group_account_invoice",
            company_id=cls.company2.id,
            company_ids=[Command.set(cls.company2.ids)],
        )
        cls.customer = cls.env["res.partner"].create({"name": "Cliente Aging SA"})
        cls.customer_b = cls.env["res.partner"].create({"name": "Cliente Abono SL"})
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor Aging SL"})

    @classmethod
    def _new_company(cls, name):
        company = cls.env["res.company"].create(
            {"name": name, "fiscalyear_last_day": 31, "fiscalyear_last_month": "12"}
        )
        cls.env["account.chart.template"]._load(
            "generic_coa", company, install_demo=False
        )
        return company

    def make_move(
        self,
        move_type,
        partner,
        amount,
        due,
        company=None,
        post=True,
        ref=None,
        name=None,
    ):
        company = company or self.company
        move = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": move_type,
                    "partner_id": partner.id,
                    "invoice_date": "2026-01-01",
                    "invoice_date_due": due,
                    "invoice_payment_term_id": False,
                    "ref": ref or False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": name or "Servicio",
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": [Command.set([])],
                            }
                        )
                    ],
                }
            )
        )
        if post:
            move.action_post()
        return move

    def agent_call(self, user, run, name, args=None, cids=None):
        return self.call(user, run, name, args or {}, cids=cids)["structuredContent"]

    def at_today(self):
        toolbox = type(self.env["xtd.ai.toolbox.account"])
        return patch.object(toolbox, "_xtd_ai_today", return_value=TODAY)

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestJournalEntries(XtdAiAccountCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = new_test_user(
            cls.env,
            "xtd_ai_accountant",
            groups=AI_GROUPS + ",account.group_account_user",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        Account = cls.env["account.account"].with_company(cls.company)
        domain = Account._check_company_domain(cls.company)
        cls.expense = Account.search(
            [*domain, ("account_type", "=", "expense")], limit=1
        )
        cls.accrual = Account.search(
            [*domain, ("account_type", "=", "liability_current")], limit=1
        )

    def entry(self, user, run, lines, **extra):
        args = {"date": "2026-10-31", "ref": "Periodificación octubre", "lines": lines}
        return self.agent_call(user, run, "create_journal_entry", args | extra)

    def balanced(self, amount=150.0):
        return [
            {"account": self.expense.code, "debit": amount, "credit": 0},
            {"account": self.accrual.code, "debit": 0, "credit": amount},
        ]

    def test_balanced_entry_is_created_in_draft(self):
        self.set_confirm(self.accountant, False)
        run, _token = self.start_run(self.accountant)
        structured = self.entry(self.accountant, run, self.balanced())
        self.assertEqual(structured["status"], "ok", structured)
        move = self.env["account.move"].browse(structured["records"][0]["id"])
        self.assertEqual((move.move_type, move.state), ("entry", "draft"))
        self.assertEqual(move.journal_id.type, "general")
        self.assertEqual(move.ref, "Periodificación octubre")
        self.assertEqual(sum(move.line_ids.mapped("debit")), 150.0)
        self.assertEqual(structured["records"][0].get("view"), "journal_items")

    def test_confirmation_card_shows_the_lines(self):
        self.set_confirm(self.accountant, True)
        run, _token = self.start_run(self.accountant)
        moves = self.env["account.move"].search_count([])
        structured = self.entry(self.accountant, run, self.balanced(80))
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("2 apuntes", structured["summary"])
        self.assertEqual(self.env["account.move"].search_count([]), moves)
        preview = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .preview
        )
        values = [row["value"] for row in preview["lines"]]
        self.assertTrue(any(v.startswith("Debe 80.00") for v in values), values)
        self.assertTrue(any(v.startswith("Haber 80.00") for v in values), values)

    def test_invalid_entries_are_refused(self):
        run, _token = self.start_run(self.accountant)
        unbalanced = self.balanced()
        unbalanced[1]["credit"] = 100
        both = self.balanced()
        both[0]["credit"] = 10
        unknown = self.balanced()
        unknown[0]["account"] = "999999999"
        for lines in (unbalanced, both, unknown):
            structured = self.entry(self.accountant, run, lines)
            self.assertEqual(structured["error"]["code"], "validation", structured)

    def test_invoicing_users_cannot_create_entries(self):
        run, _token = self.start_run(self.biller)
        status, response = self.rpc(
            self.biller,
            run,
            "tools/call",
            {"name": "create_journal_entry", "arguments": {}},
        )
        self.assertEqual((status, response["error"]["code"]), (200, -32601))

    def test_open_journal_entry_asks_the_chat_to_navigate(self):
        move = self.make_move(
            "in_invoice", self.vendor, 100, "2026-07-31", post=False, ref="F-77"
        )
        run, _token = self.start_run(self.biller)
        self.agent_call(self.biller, run, "get_invoice", {"invoice_id": move.id})
        structured = self.agent_call(
            self.biller, run, "open_journal_entry", {"invoice_id": move.id}
        )
        self.assertEqual(structured["status"], "ok", structured)
        ref = structured["records"][0]
        self.assertEqual(
            (ref["model"], ref["id"], ref["view"], ref["navigate"]),
            ("account.move", move.id, "journal_items", True),
        )
        # the form reference of get_invoice and the journal items one both stay
        views = sorted(str(r.get("view")) for r in run.record_refs)
        self.assertEqual(views, ["None", "journal_items"])

    def test_partner_zero_means_none_and_own_company_is_refused(self):
        self.set_confirm(self.accountant, False)
        run, _token = self.start_run(self.accountant)
        lines = self.balanced()
        lines[0]["partner_id"] = 0
        structured = self.entry(self.accountant, run, lines)
        self.assertEqual(structured["status"], "ok", structured)
        move = self.env["account.move"].browse(structured["records"][0]["id"])
        self.assertFalse(move.line_ids.partner_id)
        lines[0]["partner_id"] = self.company.partner_id.id
        structured = self.entry(self.accountant, run, lines)
        self.assertEqual(structured["error"]["code"], "validation", structured)

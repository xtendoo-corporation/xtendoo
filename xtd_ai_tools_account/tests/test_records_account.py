from odoo import Command
from odoo.tests import tagged

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestAccountDraftEdits(XtdAiAccountCase):
    def update(self, model, record, pairs, user=None):
        user = user or self.biller
        self.set_confirm(user, False)
        runs = self.__dict__.setdefault("_runs", {})
        if user.id not in runs:
            runs[user.id] = self.start_run(user)[0]
        return self.agent_call(
            user,
            runs[user.id],
            "update_record",
            {
                "model": model,
                "record": str(record),
                "changes": [{"field": f, "value": v} for f, v in pairs],
            },
            cids=self.company.ids,
        )

    def test_edit_draft_invoice_and_its_lines(self):
        move = self.make_move(
            "out_invoice", self.customer, 100.0, "2026-02-01", post=False
        )
        line = move.invoice_line_ids
        result = self.update(
            "account.move",
            move.id,
            [
                ("invoice_date", "2026-03-01"),
                ("ref", "PED-9"),
                ("narration", "Gracias"),
            ],
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual((str(move.invoice_date), move.ref), ("2026-03-01", "PED-9"))
        result = self.update(
            "account.move.line", line.id, [("quantity", "3"), ("name", "Horas")]
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual((line.quantity, move.amount_untaxed), (3.0, 300.0))
        for pairs in ([("price_unit", "90")], [("discount", "50")], [("tax_ids", "")]):
            self.assertEqual(
                self.update("account.move.line", line.id, pairs)["status"],
                "pending_confirmation",
                pairs,
            )
        # an invoice line takes its account from the product: refused
        account = line.account_id
        result = self.update(
            "account.move.line", line.id, [("account_id", account.code)]
        )
        self.assertEqual(result["error"]["code"], "forbidden")
        # the payment reference matches bank payments: card
        self.assertEqual(
            self.update("account.move", move.id, [("payment_reference", "X")])[
                "status"
            ],
            "pending_confirmation",
        )

    def test_posted_invoice_is_not_editable(self):
        move = self.make_move("out_invoice", self.customer, 100.0, "2026-02-01")
        result = self.update("account.move", move.id, [("ref", "X")])
        self.assertEqual(result["status"], "error", result)
        result = self.update(
            "account.move.line", move.invoice_line_ids.id, [("name", "X")]
        )
        self.assertEqual(result["status"], "error", result)
        for field in ("partner_id", "journal_id", "state", "partner_bank_id"):
            draft = self.make_move(
                "out_invoice", self.customer, 1.0, "2026-02-01", post=False
            )
            result = self.update("account.move", draft.id, [(field, "1")])
            self.assertEqual(result["error"]["code"], "forbidden", field)

    def test_manual_entry_accounts_in_draft(self):
        accounts = self.env["account.account"].search(
            [("company_ids", "in", self.company.ids), ("account_type", "=", "expense")],
            limit=2,
        )
        bank = self.env["account.account"].search(
            [
                ("company_ids", "in", self.company.ids),
                ("account_type", "=", "asset_current"),
            ],
            limit=1,
        )
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.company.id), ("type", "=", "general")], limit=1
        )
        move = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "line_ids": [
                        Command.create(
                            {"account_id": accounts[0].id, "debit": 50, "name": "A"}
                        ),
                        Command.create(
                            {"account_id": bank.id, "credit": 50, "name": "B"}
                        ),
                    ],
                }
            )
        )
        line = move.line_ids.filtered(lambda line: line.debit)
        result = self.update(
            "account.move.line",
            line.id,
            [("account_id", accounts[1].with_company(self.company).code)],
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(line.account_id, accounts[1])
        self.assertEqual(
            self.update("account.move.line", line.id, [("debit", "60")])["status"],
            "pending_confirmation",
        )
        self.assertEqual(
            self.update("account.move.line", line.id, [("quantity", "2")])["error"][
                "code"
            ],
            "forbidden",
        )
        # the undo of the account change restores the first account
        ref = result["records"][0]
        done = (
            self.env["xtd.ai.undo"]
            .with_user(self.biller)
            ._xtd_ai_undo_edit("account.move.line", line.id, ref["undo_edit"])
        )
        self.assertTrue(done["undone"], done)
        self.assertEqual(line.account_id, accounts[0])

    def test_reader_cannot_edit(self):
        move = self.make_move(
            "out_invoice", self.customer, 1.0, "2026-02-01", post=False
        )
        run = self.start_run(self.reader)[0]
        status, response = self.rpc(
            self.reader,
            run,
            "tools/call",
            {
                "name": "update_record",
                "arguments": {
                    "model": "account.move",
                    "record": str(move.id),
                    "changes": [{"field": "ref", "value": "X"}],
                },
            },
            cids=self.company.ids,
        )
        self.assertTrue("error" in response or response["result"]["isError"])
        self.assertFalse(move.ref)

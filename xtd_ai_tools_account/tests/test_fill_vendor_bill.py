import json

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestFillVendorBill(XtdAiAccountCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax = cls.company.account_purchase_tax_id
        cls.percent = f"{cls.tax.amount:g}"
        cls.multi = new_test_user(
            cls.env,
            "xtd_ai_fill_multi",
            groups=AI_GROUPS + ",account.group_account_invoice",
            company_id=cls.company.id,
            company_ids=[Command.set([cls.company.id, cls.company2.id])],
        )

    # ------------------------------------------------------------------
    def draft_bill(self, company=None, lines=(), partner=None, move_type="in_invoice"):
        return (
            self.env["account.move"]
            .with_company(company or self.company)
            .create(
                {
                    "move_type": move_type,
                    "partner_id": partner.id if partner else False,
                    "invoice_line_ids": [Command.create(line) for line in lines],
                }
            )
        )

    def fill_args(self, move, **extra):
        return {
            "move_id": move.id,
            "partner_id": self.vendor.id,
            "ref": "FRA26/900",
            "invoice_date": "2026-09-29",
            "invoice_date_due": "2026-10-29",
            "lines": [
                {
                    "description": "Material",
                    "quantity": 2,
                    "price_unit": 50,
                    "tax": self.percent,
                },
                {
                    "description": "Portes",
                    "quantity": 1,
                    "price_unit": 10,
                    "discount": 50,
                    "tax": self.percent,
                },
            ],
        } | extra

    def fill(self, user, move, cids=None, **extra):
        # one run per user and test (a second one would find the first in progress)
        runs = self.__dict__.setdefault("_fill_runs", {})
        if user not in runs:
            runs[user] = self.start_run(user)[0]
        run = runs[user]
        return self.agent_call(
            user, run, "fill_vendor_bill", self.fill_args(move, **extra), cids=cids
        )

    def confirm(self, user, structured):
        result = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .with_user(user)
            .action_confirm()
        )
        self.assertEqual(result["state"], "confirmed", result)
        return result

    def expected_total(self):
        untaxed = 2 * 50 + 10 * 0.5
        return round(untaxed * (1 + self.tax.amount / 100), 2)

    # ------------------------------------------------------------------
    def test_fill_empty_bill_always_asks_for_a_card(self):
        # confirmation of writes is off, yet filling always asks (N2)
        self.set_confirm(self.biller, False)
        move = self.draft_bill()
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("FRA26/900", structured["summary"])
        self.assertIn(self.vendor.name, structured["summary"])
        # nothing written until the user confirms
        self.assertFalse(move.invoice_line_ids)
        self.assertFalse(move.partner_id)
        preview = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .preview
        )
        self.assertEqual(len(preview["lines"]), 2)
        self.assertEqual(preview["amount_total"]["amount"], self.expected_total())
        self.assertEqual(preview["previous_lines"], [])
        self.assertEqual(preview["invoice_date"], "2026-09-29")

        result = self.confirm(self.biller, structured)
        self.assertEqual(result["records"][0]["id"], move.id)
        move.invalidate_recordset()
        self.assertEqual((move.move_type, move.state), ("in_invoice", "draft"))
        self.assertEqual(move.partner_id, self.vendor)
        self.assertEqual(move.ref, "FRA26/900")
        self.assertEqual(str(move.invoice_date), "2026-09-29")
        self.assertEqual(str(move.invoice_date_due), "2026-10-29")
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(move.invoice_line_ids[1].discount, 50)
        self.assertEqual(move.invoice_line_ids.tax_ids, self.tax)
        # the total is Odoo's, not the model's
        self.assertAlmostEqual(move.amount_total, self.expected_total())
        # no new bill, and no attachment is created
        self.assertEqual(
            self.env["account.move"].search_count(
                [("partner_id", "=", self.vendor.id), ("move_type", "=", "in_invoice")]
            ),
            1,
        )

    def test_existing_lines_need_an_explicit_choice(self):
        old = {"name": "Material previo", "quantity": 1, "price_unit": 30}
        move = self.draft_bill(lines=[old], partner=self.vendor)
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["status"], "error", structured)
        self.assertEqual(structured["error"]["code"], "validation")
        self.assertIn("on_existing_lines", structured["error"]["message"])
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertFalse(move.ref)

    def test_existing_lines_are_kept_with_append(self):
        old = {"name": "Material previo", "quantity": 1, "price_unit": 30}
        move = self.draft_bill(lines=[old], partner=self.vendor)
        structured = self.fill(self.biller, move, on_existing_lines="append")
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("conservan", structured["summary"])
        preview = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .preview
        )
        self.assertEqual(len(preview["previous_lines"]), 1)
        self.assertEqual(len(move.invoice_line_ids), 1)  # still untouched
        self.confirm(self.biller, structured)
        move.invalidate_recordset()
        self.assertEqual(len(move.invoice_line_ids), 3)
        self.assertEqual(move.invoice_line_ids[0].name, "Material previo")
        # the new lines carry the tax asked for; the old one keeps its own
        self.assertEqual(move.invoice_line_ids[1:].tax_ids, self.tax)

    def test_existing_lines_are_replaced_with_replace(self):
        old = {"name": "Material previo", "quantity": 1, "price_unit": 30}
        move = self.draft_bill(lines=[old], partner=self.vendor)
        structured = self.fill(self.biller, move, on_existing_lines="replace")
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("REEMPLAZAN", structured["summary"])
        self.assertIn("Material previo", structured["summary"])
        self.assertEqual(move.invoice_line_ids.name, "Material previo")
        self.confirm(self.biller, structured)
        move.invalidate_recordset()
        self.assertEqual(
            move.invoice_line_ids.mapped("name"), ["Material", "Portes"]
        )
        self.assertAlmostEqual(move.amount_total, self.expected_total())

    def test_posted_bill_is_rejected(self):
        move = self.draft_bill(
            lines=[{"name": "x", "quantity": 1, "price_unit": 5}], partner=self.vendor
        )
        move.invoice_date = "2026-01-01"
        move.action_post()
        structured = self.fill(self.biller, move, on_existing_lines="replace")
        self.assertEqual(structured["status"], "error", structured)
        self.assertEqual(structured["error"]["code"], "forbidden")
        self.assertEqual(move.state, "posted")
        self.assertEqual(len(move.invoice_line_ids), 1)

    def test_cancelled_bill_is_rejected(self):
        move = self.draft_bill()
        move.button_cancel()
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["error"]["code"], "forbidden", structured)
        self.assertEqual(move.state, "cancel")
        self.assertFalse(move.invoice_line_ids)

    def test_customer_invoice_and_refunds_are_rejected(self):
        for move_type in ("out_invoice", "out_refund", "in_refund"):
            move = self.draft_bill(move_type=move_type)
            structured = self.fill(self.biller, move)
            self.assertEqual(structured["status"], "error", (move_type, structured))
            self.assertEqual(structured["error"]["code"], "validation")
            self.assertFalse(move.invoice_line_ids)
            self.assertFalse(move.ref)

    def test_journal_entry_is_not_found(self):
        entry = self.draft_bill(move_type="entry")
        structured = self.fill(self.biller, entry)
        self.assertEqual(structured["error"]["code"], "not_found", structured)

    def test_other_partner_is_not_replaced(self):
        move = self.draft_bill(partner=self.customer)
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["error"]["code"], "validation", structured)
        self.assertIn(self.customer.name, structured["error"]["message"])
        self.assertEqual(move.partner_id, self.customer)

    def test_user_without_invoicing_group_cannot_call(self):
        move = self.draft_bill()
        for user in (self.reader, self.nobody):
            run, _token = self.start_run(user)
            status, response = self.rpc(
                user,
                run,
                "tools/call",
                {"name": "fill_vendor_bill", "arguments": self.fill_args(move)},
            )
            self.assertEqual(response["error"]["code"], -32601, response)
        self.assertFalse(move.invoice_line_ids)

    def test_user_without_write_access_to_the_bill_is_refused(self):
        # a rule that hides the bill from the user's writes: no sudo to get round it
        move = self.draft_bill()
        self.env["ir.rule"].create(
            {
                "name": "fill test: no writes on this bill",
                "model_id": self.env["ir.model"]._get_id("account.move"),
                "domain_force": f"[('id', '!=', {move.id})]",
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["status"], "error", structured)
        self.assertFalse(move.invoice_line_ids)

    def test_bill_of_another_company_is_not_visible(self):
        move = self.draft_bill(company=self.company2)
        structured = self.fill(self.biller, move)
        self.assertEqual(structured["error"]["code"], "not_found", structured)
        self.assertFalse(move.invoice_line_ids)
        # the user of the other company works fine
        structured = self.fill(self.biller2, move, cids=[self.company2.id])
        self.assertEqual(structured["status"], "pending_confirmation", structured)

    def test_company_of_the_bill_must_be_active(self):
        move = self.draft_bill(company=self.company2)
        run, _token = self.start_run(self.multi)
        structured = self.agent_call(
            self.multi,
            run,
            "fill_vendor_bill",
            self.fill_args(move),
            cids=[self.company.id],
        )
        self.assertEqual(structured["status"], "error", structured)
        self.assertFalse(move.invoice_line_ids)

    def test_bill_of_the_second_company_is_filled_in_its_company(self):
        move = self.draft_bill(company=self.company2)
        tax2 = self.company2.account_purchase_tax_id
        run, _token = self.start_run(self.multi)
        args = self.fill_args(move)
        for line in args["lines"]:
            line["tax"] = f"{tax2.amount:g}"
        structured = self.agent_call(
            self.multi,
            run,
            "fill_vendor_bill",
            args,
            cids=[self.company.id, self.company2.id],
        )
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn(self.company2.name, structured["summary"])
        result = self.confirm(self.multi, structured)
        move = self.env["account.move"].browse(result["records"][0]["id"])
        self.assertEqual(move.company_id, self.company2)
        self.assertEqual(move.invoice_line_ids.tax_ids, tax2)

    def test_missing_ref_or_date_is_a_schema_error(self):
        move = self.draft_bill()
        run, _token = self.start_run(self.biller)
        for key in ("ref", "invoice_date", "move_id"):
            args = self.fill_args(move)
            args.pop(key)
            structured = self.agent_call(self.biller, run, "fill_vendor_bill", args)
            self.assertEqual(structured["status"], "error", (key, structured))
        self.assertFalse(move.invoice_line_ids)

    def test_new_supplier_on_an_empty_bill(self):
        self.biller.group_ids += self.env.ref("base.group_partner_manager")
        move = self.draft_bill()
        structured = self.fill(
            self.biller,
            move,
            partner_id=0,
            new_partner={"name": "TU RUEDA, S.L.", "vat": "B21218474"},
        )
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("TU RUEDA, S.L.", structured["summary"])
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "TU RUEDA, S.L.")])
        )
        self.confirm(self.biller, structured)
        move.invalidate_recordset()
        self.assertEqual(move.partner_id.name, "TU RUEDA, S.L.")

    def test_tool_is_listed_with_its_schema(self):
        run, _token = self.start_run(self.biller)
        _status, response = self.rpc(self.biller, run, "tools/list", {})
        tool = {t["name"]: t for t in response["result"]["tools"]}["fill_vendor_bill"]
        self.assertNotIn("attachment_id", tool["inputSchema"]["properties"])
        self.assertIn("move_id", tool["inputSchema"]["required"])
        json.dumps(tool)

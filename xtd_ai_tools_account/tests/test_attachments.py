from odoo.tests import tagged

from odoo.addons.xtd_ai.tests.common import make_pdf

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestAccountAttachments(XtdAiAccountCase):
    def bill_args(self, attachment_id=None):
        args = {
            "partner_id": self.vendor.id,
            "ref": "F-2026/77",
            "invoice_date": "2026-03-01",
            "lines": [{"description": "Material", "quantity": 2, "price_unit": 50}],
        }
        if attachment_id is not None:
            args["attachment_id"] = attachment_id
        return args

    def confirm(self, user, structured):
        result = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .with_user(user)
            .action_confirm()
        )
        self.assertEqual(result["state"], "confirmed", result)
        return self.env["account.move"].browse(result["records"][0]["id"])

    def test_vendor_bill_with_attachment(self):
        # confirmation is switched off, yet the attachment forces it
        self.set_confirm(self.biller, False)
        raw = make_pdf()
        att = self.upload(self.biller, raw=raw, name="factura-proveedor.pdf")
        run, _token = self.start_run(self.biller, "", attachment_ids=[att.id])
        env_moves = self.env["account.move"].search_count([])
        structured = self.agent_call(
            self.biller, run, "create_vendor_bill", self.bill_args(att.id)
        )
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("factura-proveedor.pdf", structured["summary"])
        self.assertEqual(self.env["account.move"].search_count([]), env_moves)
        preview = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .preview
        )
        self.assertEqual(
            preview["attachment"]["untrusted_text"], "factura-proveedor.pdf"
        )
        self.assertEqual(preview["amount_untaxed"]["amount"], 100.0)

        move = self.confirm(self.biller, structured)
        self.assertEqual((move.move_type, move.state), ("in_invoice", "draft"))
        copy = move.message_main_attachment_id
        self.assertTrue(copy)
        self.assertEqual(
            (copy.res_model, copy.res_id, copy.name, copy.raw),
            ("account.move", move.id, "factura-proveedor.pdf", raw),
        )
        self.assertNotEqual(copy, att)
        # the chat copy is untouched
        self.assertEqual((att.res_model, att.raw), ("xtd.ai.conversation", raw))
        self.assertEqual(copy.create_uid, self.biller)

    def test_vendor_bill_from_document_requires_ref_and_date(self):
        att = self.upload(self.biller, raw=make_pdf(), name="factura.pdf")
        run, _token = self.start_run(self.biller, "", attachment_ids=[att.id])
        moves = self.env["account.move"].search_count([])
        for missing in (("ref",), ("invoice_date",), ("ref", "invoice_date")):
            args = self.bill_args(att.id)
            for key in missing:
                args.pop(key)
            structured = self.agent_call(self.biller, run, "create_vendor_bill", args)
            self.assertEqual(structured["status"], "error", structured)
            self.assertEqual(structured["error"]["code"], "validation")
            for key in missing:
                self.assertIn(key, structured["error"]["message"])
        self.assertEqual(self.env["account.move"].search_count([]), moves)
        # a vendor bill always needs them, document or not (required in the schema)
        args = self.bill_args()
        args.pop("ref")
        args.pop("invoice_date")
        structured = self.agent_call(self.biller, run, "create_vendor_bill", args)
        self.assertEqual(structured["status"], "error", structured)
        self.assertEqual(structured["error"]["code"], "validation")

    def test_due_date_from_document_wins_over_payment_term(self):
        term = self.env.ref(
            "account.account_payment_term_30days", raise_if_not_found=False
        )
        if term:
            self.vendor.with_company(self.vendor.company_id or self.env.company).write(
                {"property_supplier_payment_term_id": term.id}
            )
        att = self.upload(self.biller, raw=make_pdf(), name="factura.pdf")
        run, _token = self.start_run(self.biller, "", attachment_ids=[att.id])
        args = self.bill_args(att.id) | {"invoice_date_due": "2026-04-15"}
        structured = self.agent_call(self.biller, run, "create_vendor_bill", args)
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("vence 2026-04-15", structured["summary"])
        preview = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .preview
        )
        self.assertEqual(preview["invoice_date_due"], "2026-04-15")
        move = self.confirm(self.biller, structured)
        self.assertEqual(str(move.invoice_date_due), "2026-04-15")
        self.assertFalse(move.invoice_payment_term_id)

    def test_due_date_before_invoice_date_is_rejected(self):
        att = self.upload(self.biller, raw=make_pdf(), name="factura.pdf")
        run, _token = self.start_run(self.biller, "", attachment_ids=[att.id])
        args = self.bill_args(att.id) | {"invoice_date_due": "2026-02-01"}
        structured = self.agent_call(self.biller, run, "create_vendor_bill", args)
        self.assertEqual(structured["status"], "error", structured)
        self.assertEqual(structured["error"]["code"], "validation")
        self.assertIn("vencimiento", structured["error"]["message"])

    def test_customer_invoice_with_attachment(self):
        att = self.upload(self.biller)
        run, _token = self.start_run(self.biller, "mira", attachment_ids=[att.id])
        structured = self.agent_call(
            self.biller,
            run,
            "create_customer_invoice",
            {
                "partner_id": self.customer.id,
                "lines": [{"description": "Servicio", "quantity": 1, "price_unit": 10}],
                "attachment_id": att.id,
            },
        )
        move = self.confirm(self.biller, structured)
        self.assertEqual(move.message_main_attachment_id.res_id, move.id)

    def test_without_attachment_unchanged(self):
        self.set_confirm(self.biller, False)
        run, _token = self.start_run(self.biller)
        structured = self.agent_call(
            self.biller, run, "create_vendor_bill", self.bill_args()
        )
        self.assertEqual(structured["status"], "ok", structured)
        self.assertNotIn("attachment", structured["data"])

    def test_attachment_of_another_conversation_is_rejected(self):
        # an attachment of a conversation that is not the run's
        other_att = self.upload(self.biller2)
        mine = self.upload(self.biller)
        run, _token = self.start_run(self.biller, "x", attachment_ids=[mine.id])
        for bad in (other_att.id, 987654321):
            structured = self.agent_call(
                self.biller, run, "create_vendor_bill", self.bill_args(bad)
            )
            self.assertEqual(structured["status"], "error", structured)
            self.assertEqual(structured["error"]["code"], "not_found")
        # an unlinked attachment of my own conversation is not valid either
        loose = self.upload(self.biller, name="suelto.pdf")
        structured = self.agent_call(
            self.biller, run, "create_vendor_bill", self.bill_args(loose.id)
        )
        self.assertEqual(structured["error"]["code"], "not_found")
        self.assertFalse(self.env["account.move"].search([("ref", "=", "F-2026/77")]))

    def test_attachment_id_must_be_integer(self):
        run, _token = self.start_run(self.biller)
        structured = self.agent_call(
            self.biller,
            run,
            "create_vendor_bill",
            self.bill_args() | {"attachment_id": "12"},
        )
        self.assertEqual(structured["error"]["code"], "validation")

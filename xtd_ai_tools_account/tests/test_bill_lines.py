from odoo.tests import tagged

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestBillLines(XtdAiAccountCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_tax = cls.company.account_purchase_tax_id
        Tax = cls.env["account.tax"].with_company(cls.company)
        cls.tax_goods = Tax.create(
            {"name": "IVA 21% bienes AI", "amount": 21, "type_tax_use": "purchase"}
        )
        cls.tax_services = Tax.create(
            {"name": "IVA 21% servicios AI", "amount": 21, "type_tax_use": "purchase"}
        )

    def bill(self, user, run, lines, **extra):
        args = {
            "partner_id": self.vendor.id,
            "ref": "FRA26/604",
            "invoice_date": "2026-09-29",
            "lines": lines,
        } | extra
        return self.agent_call(user, run, "create_vendor_bill", args)

    def created_move(self, structured):
        self.assertEqual(structured["status"], "ok", structured)
        moves = [r for r in structured["records"] if r["model"] == "account.move"]
        return self.env["account.move"].browse(moves[0]["id"])

    def test_discount_and_default_tax_by_percent(self):
        self.set_confirm(self.biller, False)
        run, _token = self.start_run(self.biller)
        percent = f"{self.default_tax.amount:g}"
        structured = self.bill(
            self.biller,
            run,
            [
                {
                    "description": "Desmontaje y montaje",
                    "quantity": 2,
                    "price_unit": 6.5,
                    "discount": 30,
                    "tax": percent,
                }
            ],
        )
        move = self.created_move(structured)
        line = move.invoice_line_ids
        self.assertEqual(line.discount, 30)
        self.assertEqual(line.tax_ids, self.default_tax)
        self.assertAlmostEqual(move.amount_untaxed, 9.10)
        self.assertEqual(move.state, "draft")

    def test_ambiguous_percent_asks_and_exact_name_works(self):
        self.set_confirm(self.biller, False)
        run, _token = self.start_run(self.biller)
        if self.default_tax.amount == 21:
            self.skipTest("the generic chart's default purchase tax is 21%")
        line = {"description": "Cubierta", "quantity": 2, "price_unit": 110.09}
        structured = self.bill(self.biller, run, [line | {"tax": "21"}])
        self.assertEqual(structured["status"], "error", structured)
        self.assertEqual(structured["error"]["code"], "ambiguous")
        self.assertIn("IVA 21% servicios AI", structured["error"]["message"])
        structured = self.bill(
            self.biller, run, [line | {"tax": "IVA 21% servicios AI"}]
        )
        move = self.created_move(structured)
        self.assertEqual(move.invoice_line_ids.tax_ids, self.tax_services)
        self.assertAlmostEqual(move.amount_tax, 46.24)

    def test_unknown_tax_is_a_validation_error(self):
        run, _token = self.start_run(self.biller)
        structured = self.bill(
            self.biller,
            run,
            [{"description": "X", "quantity": 1, "price_unit": 1, "tax": "37"}],
        )
        self.assertEqual(structured["error"]["code"], "validation", structured)

    def test_untaxed_lines_are_flagged_in_the_preview(self):
        # a free-text line takes the expense account's taxes: none here
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.company.id), ("type", "=", "purchase")], limit=1
        )
        journal.default_account_id.tax_ids = False
        self.set_confirm(self.biller, True)
        run, _token = self.start_run(self.biller)
        structured = self.bill(
            self.biller,
            run,
            [
                {
                    "description": "Con impuesto",
                    "quantity": 1,
                    "price_unit": 10,
                    "tax": "IVA 21% bienes AI",
                },
                {"description": "Sin impuesto", "quantity": 1, "price_unit": 10},
            ],
        )
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("Atención: 1 líneas sin impuestos", structured["summary"])

    def test_new_supplier_is_created_with_the_bill_on_confirmation(self):
        # creating the supplier needs the user's own right to create contacts
        self.biller.group_ids += self.env.ref("base.group_partner_manager")
        self.set_confirm(self.biller, True)
        run, _token = self.start_run(self.biller)
        partners = self.env["res.partner"].search_count([])
        structured = self.bill(
            self.biller,
            run,
            [{"description": "Cubierta", "quantity": 2, "price_unit": 110.09}],
            partner_id=0,
            new_partner={
                "name": "TU RUEDA, S.L.",
                "vat": "B21218474",
                "city": "La Palma del Condado",
                "country_code": "ES",
            },
        )
        self.assertEqual(structured["status"], "pending_confirmation", structured)
        self.assertIn("TU RUEDA, S.L.", structured["summary"])
        self.assertIn("proveedor", structured["summary"])
        self.assertEqual(self.env["res.partner"].search_count([]), partners)
        result = (
            self.env(su=True)["xtd.ai.pending_action"]
            .browse(structured["pending_action_id"])
            .with_user(self.biller)
            .action_confirm()
        )
        self.assertEqual(result["state"], "confirmed", result)
        move_ref = [r for r in result["records"] if r["model"] == "account.move"][0]
        move = self.env["account.move"].browse(move_ref["id"])
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.partner_id.name, "TU RUEDA, S.L.")
        self.assertTrue(move.partner_id.is_company)
        self.assertFalse(move.partner_id.parent_id)
        self.assertEqual(move.partner_id.country_id.code, "ES")
        self.assertEqual(self.env["res.partner"].search_count([]), partners + 1)

    def test_new_supplier_rules(self):
        run, _token = self.start_run(self.biller)
        line = [{"description": "X", "quantity": 1, "price_unit": 1}]
        # partner 0 without data
        structured = self.bill(self.biller, run, line, partner_id=0)
        self.assertEqual(structured["error"]["code"], "validation", structured)
        # both an existing partner and new data
        structured = self.bill(
            self.biller, run, line, new_partner={"name": "Otro Proveedor SL"}
        )
        self.assertEqual(structured["error"]["code"], "validation", structured)
        # an existing supplier is never duplicated
        structured = self.bill(
            self.biller, run, line, partner_id=0, new_partner={"name": self.vendor.name}
        )
        self.assertEqual(structured["error"]["code"], "validation", structured)
        self.assertIn(str(self.vendor.id), structured["error"]["message"])

# Copyright 2026 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestPaymentReturnLineMatch(TransactionCase):
    """Tests for xtendoo_account_payment_return_import_iso20022_match.

    What is tested:
    - _resolve_partner_from_name: exact name match assigns partner_id.
    - _resolve_partner_from_name: unknown name leaves partner_id empty.
    - _resolve_partner_from_name: ambiguous name (multiple hits) leaves
      partner_id empty.
    - match_invoice_by_concept: finds invoice by concept and sets move_line_ids.
    - match_invoice_by_concept: no match when concept does not correspond to
      any invoice.
    - match_move_lines_by_concept: fallback matches reconciled move lines when
      no invoice is found.
    - _find_match: already-matched lines (from super()) are not overwritten.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.ref("base.main_company")

        # Journal
        cls.bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ES5821008381442200052427",
                "bank_name": "CAIXABANK",
                "company_id": cls.company.id,
                "partner_id": cls.company.partner_id.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Bank Journal ISO",
                "code": "TISO",
                "type": "bank",
                "bank_account_id": cls.bank_account.id,
                "company_id": cls.company.id,
            }
        )

        # Unique customer partners
        cls.partner_unique = cls.env["res.partner"].create(
            {
                "name": "ROSA MARIA SAENZ DUENAS",
                "customer_rank": 1,
            }
        )
        # Two partners with the same name to test ambiguity
        cls.partner_ambiguous_1 = cls.env["res.partner"].create(
            {
                "name": "CLIENTE DUPLICADO SA",
                "customer_rank": 1,
            }
        )
        cls.partner_ambiguous_2 = cls.env["res.partner"].create(
            {
                "name": "CLIENTE DUPLICADO SA",
                "customer_rank": 1,
            }
        )

        # Accounts
        receivable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        income_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )

        # Invoice for cls.partner_unique, name = HERM/2026/00536
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_unique.id,
                "journal_id": cls.env["account.journal"]
                .search([("type", "=", "sale"), ("company_id", "=", cls.company.id)], limit=1)
                .id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Cuota hermandad",
                            "quantity": 1,
                            "price_unit": 15.0,
                            "account_id": income_account.id,
                        },
                    )
                ],
            }
        )
        invoice._post()
        # Force invoice name to match XML concept
        invoice.name = "HERM/2026/00536"

        # Register payment for the invoice
        payment = cls.env["account.payment"].create(
            {
                "partner_id": cls.partner_unique.id,
                "amount": 15.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "journal_id": cls.journal.id,
            }
        )
        payment.action_post()

        # Reconcile payment with invoice
        (invoice.line_ids.filtered(lambda l: l.account_type == "asset_receivable")
         | payment.move_id.line_ids.filtered(
             lambda l: l.account_id == receivable_account
         )).reconcile()

        cls.invoice = invoice
        cls.payment = payment
        cls.receivable_account = receivable_account

        # Payment return header (draft)
        cls.payment_return = cls.env["payment.return"].create(
            {
                "journal_id": cls.journal.id,
                "date": "2026-04-15",
            }
        )

    def _make_line(self, concept=None, partner_name=None, reference="2571"):
        """Helper to create a payment.return.line in the test payment return."""
        vals = {
            "return_id": self.payment_return.id,
            "reference": reference,
            "amount": 15.0,
        }
        if concept:
            vals["concept"] = concept
        if partner_name:
            vals["partner_name"] = partner_name
        return self.env["payment.return.line"].create(vals)

    def test_resolve_partner_exact_name_match(self):
        """_resolve_partner_from_name assigns partner when name is unique."""
        line = self._make_line(partner_name="ROSA MARIA SAENZ DUENAS")
        line._resolve_partner_from_name()
        self.assertEqual(line.partner_id, self.partner_unique)

    def test_resolve_partner_unknown_name(self):
        """_resolve_partner_from_name leaves partner_id empty for unknown name."""
        line = self._make_line(partner_name="NOMBRE QUE NO EXISTE EN BD")
        line._resolve_partner_from_name()
        self.assertFalse(line.partner_id)

    def test_resolve_partner_ambiguous_name(self):
        """_resolve_partner_from_name leaves partner_id empty for ambiguous name."""
        line = self._make_line(partner_name="CLIENTE DUPLICADO SA")
        line._resolve_partner_from_name()
        self.assertFalse(line.partner_id)

    def test_match_invoice_by_concept_sets_move_line_ids(self):
        """match_invoice_by_concept finds invoice and sets move_line_ids."""
        line = self._make_line(
            concept="HERM/2026/00536",
            partner_name="ROSA MARIA SAENZ DUENAS",
        )
        line.partner_id = self.partner_unique
        line.match_invoice_by_concept()
        self.assertTrue(line.move_line_ids)

    def test_match_invoice_by_concept_no_match(self):
        """match_invoice_by_concept leaves move_line_ids empty when no invoice found."""
        line = self._make_line(concept="HERM/2099/99999")
        line.match_invoice_by_concept()
        self.assertFalse(line.move_line_ids)

    def test_match_move_lines_by_concept_fallback(self):
        """match_move_lines_by_concept sets move_line_ids from reconciled AML."""
        # Find the reconciled payment AML and set its ref to our concept
        payment_aml = self.payment.move_id.line_ids.filtered(
            lambda l: l.account_id == self.receivable_account
        )
        payment_aml.ref = "HERM/2026/CONCEPTO-FALLBACK"

        line = self._make_line(concept="HERM/2026/CONCEPTO-FALLBACK")
        line.partner_id = self.partner_unique
        line.match_move_lines_by_concept()
        self.assertTrue(line.move_line_ids)

    def test_find_match_already_matched_lines_not_overwritten(self):
        """_find_match does not overwrite lines already matched by super()."""
        line = self._make_line(
            concept="HERM/2026/00536",
            partner_name="ROSA MARIA SAENZ DUENAS",
            reference="2571",
        )
        # Pre-assign move_line_ids simulating super() already matched it
        payment_aml = self.payment.move_id.line_ids.filtered(
            lambda l: l.account_id == self.receivable_account
        )
        line.move_line_ids = payment_aml.ids
        original_ids = line.move_line_ids.ids

        line._find_match()

        self.assertEqual(line.move_line_ids.ids, original_ids)

    def test_find_match_full_flow_concept_matching(self):
        """_find_match resolves partner and move_line_ids via concept strategy."""
        line = self._make_line(
            concept="HERM/2026/00536",
            partner_name="ROSA MARIA SAENZ DUENAS",
            reference="NONEXISTENT_REFERENCE",
        )
        line._find_match()
        self.assertEqual(line.partner_id, self.partner_unique)
        self.assertTrue(line.move_line_ids)


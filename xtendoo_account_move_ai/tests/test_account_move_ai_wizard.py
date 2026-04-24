# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


AI_SALARY_RESPONSE = json.dumps(
    {
        "document_type": "salary",
        "document_type_reason": "Contains gross salary and social security lines",
        "supplier": {"name": "ACME Corp", "vat": "B12345678"},
        "date": "2026-03-31",
        "reference": "NOM-2026-03",
        "currency": "EUR",
        "journal_lines": [
            {
                "account_code": "6400",
                "account_name": "Sueldos y salarios",
                "description": "Salario bruto",
                "debit": 2500.0,
                "credit": 0.0,
            },
            {
                "account_code": "4751",
                "account_name": "H.P. acreedora por retenciones",
                "description": "IRPF retenido",
                "debit": 0.0,
                "credit": 375.0,
            },
            {
                "account_code": "4650",
                "account_name": "Remuneraciones pendientes de pago",
                "description": "Salario neto a pagar",
                "debit": 0.0,
                "credit": 2125.0,
            },
        ],
        "totals": {"subtotal": 2500.0, "tax_amount": 0.0, "total": 2500.0},
    }
)


class TestAccountMoveAIWizard(TransactionCase):
    """Functional tests for the AI wizard that creates journal entries from documents."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configure AI connector params
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", "gemini")
        ICP.set_param("xtendoo_ai_connector.ai_api_key", "fake-key")
        ICP.set_param("xtendoo_ai_connector.ai_model", "gemini-2.5-flash")

        # Create a draft journal entry
        journal = cls.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )
        cls.move = cls.env["account.move"].create(
            {"move_type": "entry", "journal_id": journal.id}
        )

        # Create a fake attachment
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "payslip_march.pdf",
                "datas": base64.b64encode(b"fake-pdf-content"),
                "mimetype": "application/pdf",
                "res_model": "account.move",
                "res_id": cls.move.id,
            }
        )

    def _make_wizard(self):
        return self.env["account.move.ai.wizard"].create(
            {
                "move_id": self.move.id,
                "attachment_id": self.attachment.id,
            }
        )

    def test_action_analyze_no_attachment_raises(self):
        wizard = self.env["account.move.ai.wizard"].create(
            {"move_id": self.move.id}
        )
        with self.assertRaises(UserError):
            wizard.action_analyze()

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_action_analyze_sets_preview_state(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_SALARY_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertEqual(wizard.detected_document_type, "salary")
        self.assertTrue(wizard.ai_json_result)

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_action_analyze_empty_response_raises(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = ""
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard.action_analyze()

    def test_action_apply_without_analyze_raises(self):
        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard.action_apply()

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_full_flow_analyze_and_apply(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_SALARY_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertEqual(wizard.detected_document_type, "salary")

        wizard.action_apply()

        self.assertEqual(self.move.ai_document_type, "salary")
        self.assertTrue(self.move.ai_processed)

    def test_account_move_ai_fields_exist(self):
        self.assertIn("ai_document_type", self.move._fields)
        self.assertIn("ai_processed", self.move._fields)
        self.assertIn("ai_has_corrections", self.move._fields)

    def test_ai_has_corrections_set_on_write_after_processing(self):
        self.move.write({"ai_processed": True, "ai_has_corrections": False})
        self.move.write({"ref": "MANUAL-CHANGE"})
        self.assertTrue(self.move.ai_has_corrections)


class TestAccountMoveAIWizardExtended(TransactionCase):
    """Extended coverage for all branches of AccountMoveAIWizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", "gemini")
        ICP.set_param("xtendoo_ai_connector.ai_api_key", "fake-key")
        ICP.set_param("xtendoo_ai_connector.ai_model", "gemini-2.5-flash")

        journal = cls.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )
        cls.move = cls.env["account.move"].create(
            {"move_type": "entry", "journal_id": journal.id}
        )
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "test.pdf",
                "datas": base64.b64encode(b"fake-pdf"),
                "mimetype": "application/pdf",
                "res_model": "account.move",
                "res_id": cls.move.id,
            }
        )

    def _make_wizard(self):
        return self.env["account.move.ai.wizard"].create(
            {"move_id": self.move.id, "attachment_id": self.attachment.id}
        )

    def _patch_provider(self, response_text):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = response_text
        patcher = patch(
            "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
            ".AccountMoveAIWizard._get_ai_provider",
            return_value=mock_provider,
        )
        return patcher

    # --- action_analyze branches ---

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_analyze_ai_exception_raises_userror(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.side_effect = Exception("API timeout")
        mock_get_provider.return_value = mock_provider

        with self.assertRaises(UserError) as ctx:
            self._make_wizard().action_analyze()
        self.assertIn("API timeout", str(ctx.exception))

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_analyze_invalid_json_raises_userror(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = "not json at all {broken"
        mock_get_provider.return_value = mock_provider

        with self.assertRaises(UserError) as ctx:
            self._make_wizard().action_analyze()
        self.assertIn("JSON", str(ctx.exception))

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_analyze_json_in_markdown_block_parsed_correctly(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = (
            "```json\n"
            '{"document_type": "expense", "document_type_reason": "test",'
            ' "journal_lines": [], "totals": {}}\n'
            "```"
        )
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.detected_document_type, "expense")

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_analyze_bare_json_regex_fallback(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = (
            "Here is the result: "
            '{"document_type": "income", "document_type_reason": "test",'
            ' "journal_lines": [], "totals": {}}'
            " That is all."
        )
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.detected_document_type, "income")

    # --- action_apply branches ---

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_apply_on_posted_move_raises_userror(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "document_type": "expense",
                "document_type_reason": "test",
                "journal_lines": [],
                "totals": {},
            }
        )
        mock_get_provider.return_value = mock_provider

        journal = self.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )
        posted_move = self.env["account.move"].create(
            {"move_type": "entry", "journal_id": journal.id}
        )
        # Create a minimal balanced entry and post it
        account = self.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        account2 = self.env["account.account"].search(
            [("account_type", "=", "liability_current")], limit=1
        )
        if account and account2:
            posted_move.write(
                {
                    "line_ids": [
                        (0, 0, {"account_id": account.id, "debit": 100, "credit": 0}),
                        (0, 0, {"account_id": account2.id, "debit": 0, "credit": 100}),
                    ]
                }
            )
            posted_move.action_post()

            attachment = self.env["ir.attachment"].create(
                {
                    "name": "t.pdf",
                    "datas": base64.b64encode(b"x"),
                    "mimetype": "application/pdf",
                    "res_model": "account.move",
                    "res_id": posted_move.id,
                }
            )
            wizard = self.env["account.move.ai.wizard"].create(
                {"move_id": posted_move.id, "attachment_id": attachment.id}
            )
            wizard.action_analyze()
            with self.assertRaises(UserError):
                wizard.action_apply()

    # --- _prepare_files branches ---

    def test_prepare_files_image_returns_raw(self):
        wizard = self._make_wizard()
        result = wizard._prepare_files(b"img-data", "image/png")
        self.assertEqual(result, [{"data": b"img-data", "mime_type": "image/png"}])

    def test_prepare_files_pdf_no_convert_returns_raw(self):
        import odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard as mod
        original = mod.convert_from_bytes
        mod.convert_from_bytes = None
        try:
            wizard = self._make_wizard()
            result = wizard._prepare_files(b"pdf-data", "application/pdf")
            self.assertEqual(result, [{"data": b"pdf-data", "mime_type": "application/pdf"}])
        finally:
            mod.convert_from_bytes = original

    def test_prepare_files_pdf_conversion_exception_fallback(self):
        import odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard as mod

        def bad_convert(*args, **kwargs):
            raise Exception("ghostscript not found")

        original = mod.convert_from_bytes
        mod.convert_from_bytes = bad_convert
        try:
            wizard = self._make_wizard()
            result = wizard._prepare_files(b"pdf-data", "application/pdf")
            self.assertEqual(result, [{"data": b"pdf-data", "mime_type": "application/pdf"}])
        finally:
            mod.convert_from_bytes = original

    # --- _apply_to_move branches ---

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_apply_writes_date_and_ref(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "document_type": "expense",
                "document_type_reason": "test",
                "date": "2026-03-15",
                "reference": "EXP-001",
                "journal_lines": [],
                "totals": {},
            }
        )
        mock_get_provider.return_value = mock_provider

        journal = self.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )
        move = self.env["account.move"].create(
            {"move_type": "entry", "journal_id": journal.id}
        )
        wizard = self.env["account.move.ai.wizard"].create(
            {"move_id": move.id, "attachment_id": self.attachment.id}
        )
        wizard.action_analyze()
        wizard.action_apply()

        self.assertEqual(str(move.date), "2026-03-15")
        self.assertEqual(move.ref, "EXP-001")

    @patch(
        "odoo.addons.xtendoo_account_move_ai.wizards.account_move_ai_wizard"
        ".AccountMoveAIWizard._get_ai_provider"
    )
    def test_apply_invalid_date_does_not_crash(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "document_type": "expense",
                "document_type_reason": "test",
                "date": "not-a-date",
                "journal_lines": [],
                "totals": {},
            }
        )
        mock_get_provider.return_value = mock_provider

        journal = self.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )
        move = self.env["account.move"].create(
            {"move_type": "entry", "journal_id": journal.id}
        )
        wizard = self.env["account.move.ai.wizard"].create(
            {"move_id": move.id, "attachment_id": self.attachment.id}
        )
        wizard.action_analyze()
        # Should not raise despite bad date
        wizard.action_apply()
        self.assertTrue(move.ai_processed)

    # --- _find_partner branches ---

    def test_find_partner_none_returns_none(self):
        wizard = self._make_wizard()
        self.assertIsNone(wizard._find_partner(None))

    def test_find_partner_empty_dict_returns_none(self):
        wizard = self._make_wizard()
        self.assertIsNone(wizard._find_partner({}))

    def test_find_partner_by_vat(self):
        partner = self.env["res.partner"].create(
            {"name": "VAT Partner", "vat": "ES99999999R"}
        )
        wizard = self._make_wizard()
        found = wizard._find_partner({"vat": "ES99999999R", "name": "Whatever"})
        self.assertEqual(found.id, partner.id)

    def test_find_partner_by_name_fallback(self):
        partner = self.env["res.partner"].create(
            {"name": "Empresa Unica SA 7823"}
        )
        wizard = self._make_wizard()
        found = wizard._find_partner({"vat": None, "name": "Empresa Unica SA 7823"})
        self.assertEqual(found.id, partner.id)

    def test_find_partner_unknown_returns_none(self):
        wizard = self._make_wizard()
        result = wizard._find_partner(
            {"vat": "ZZZZ999X", "name": "Empresa Inexistente XYZABC9999"}
        )
        self.assertIsNone(result)

    # --- _find_or_create_account branches ---

    def test_find_or_create_account_empty_code_returns_none(self):
        wizard = self._make_wizard()
        self.assertIsNone(wizard._find_or_create_account("", "Some Account"))

    def test_find_or_create_account_unknown_code_returns_none(self):
        wizard = self._make_wizard()
        result = wizard._find_or_create_account("99999ZZZZ", "Fake Account")
        self.assertIsNone(result)

    def test_find_or_create_account_known_code_returns_account(self):
        account = self.env["account.account"].search([], limit=1)
        if not account:
            return
        wizard = self._make_wizard()
        result = wizard._find_or_create_account(account.code, account.name)
        self.assertEqual(result.id, account.id)

    # --- action_open_ai_document_wizard ---

    def test_action_open_ai_document_wizard_returns_act_window(self):
        result = self.move.action_open_ai_document_wizard()
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "account.move.ai.wizard")
        self.assertEqual(result["context"]["default_move_id"], self.move.id)

    # --- AccountMove.write override branches ---

    def test_write_only_ai_internal_fields_no_corrections_flag(self):
        self.move.write({"ai_processed": True, "ai_has_corrections": False})
        # Writing only internal AI fields must NOT set ai_has_corrections=True
        self.move.write({"ai_document_type": "expense"})
        self.assertFalse(self.move.ai_has_corrections)

    def test_write_user_field_when_not_processed_no_corrections_flag(self):
        self.move.write({"ai_processed": False, "ai_has_corrections": False})
        self.move.write({"ref": "SOME-REF"})
        self.assertFalse(self.move.ai_has_corrections)

    def test_write_explicit_false_corrections_is_respected(self):
        self.move.write({"ai_processed": True, "ai_has_corrections": True})
        self.move.write({"ref": "NEW-REF", "ai_has_corrections": False})
        # When caller explicitly passes ai_has_corrections=False, it should stay False
        self.assertFalse(self.move.ai_has_corrections)

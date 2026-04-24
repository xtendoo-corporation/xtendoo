# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


AI_CRM_RESPONSE = json.dumps(
    {
        "contact_name": "María García",
        "company_name": "Distribuciones SL",
        "email": "maria@distribuciones.es",
        "phone": "+34 612 345 678",
        "mobile": None,
        "website": "https://distribuciones.es",
        "street": "Calle Mayor 10",
        "city": "Madrid",
        "zip": "28001",
        "country_name": "Spain",
        "expected_revenue": 15000.0,
        "description": "Customer interested in purchasing logistics software for their warehouse.",
        "tags": ["logistics", "warehouse"],
        "priority": "1",
        "notes": "Mentioned urgency for Q2 2026 deployment.",
    }
)


class TestCrmLeadAIWizard(TransactionCase):
    """Functional tests for the AI enrichment wizard for CRM leads."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", "gemini")
        ICP.set_param("xtendoo_ai_connector.ai_api_key", "fake-key")
        ICP.set_param("xtendoo_ai_connector.ai_model", "gemini-2.5-flash")

        cls.lead = cls.env["crm.lead"].create({"name": "Test Lead"})

    def _make_wizard(self, text="Contact me ASAP"):
        return self.env["crm.lead.ai.wizard"].create(
            {"lead_id": self.lead.id, "source_text": text}
        )

    def test_action_analyze_empty_text_raises(self):
        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": self.lead.id, "source_text": "   "}
        )
        with self.assertRaises(UserError):
            wizard.action_analyze()

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_action_analyze_sets_preview_state(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_CRM_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard("I need a warehouse solution")
        wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertEqual(wizard.preview_contact_name, "María García")
        self.assertEqual(wizard.preview_email, "maria@distribuciones.es")
        self.assertTrue(wizard.ai_json_result)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_action_analyze_empty_ai_response_raises(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = ""
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard("Some text")
        with self.assertRaises(UserError):
            wizard.action_analyze()

    def test_action_apply_without_analyze_raises(self):
        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard.action_apply()

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_full_flow_analyze_and_apply(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_CRM_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard("Contact: María García, company: Distribuciones SL")
        wizard.action_analyze()
        wizard.action_apply()

        self.assertEqual(self.lead.email_from, "maria@distribuciones.es")
        self.assertEqual(self.lead.phone, "+34 612 345 678")
        self.assertTrue(self.lead.ai_enriched)
        self.assertTrue(self.lead.ai_source_text)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_does_not_overwrite_existing_fields(self, mock_get_provider):
        """Apply should NOT overwrite fields that already have data."""
        self.lead.write({"email_from": "existing@email.com"})

        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_CRM_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard("Some text")
        wizard.action_analyze()
        wizard.action_apply()

        # Original email must be preserved
        self.assertEqual(self.lead.email_from, "existing@email.com")

    def test_crm_lead_ai_fields_exist(self):
        self.assertIn("ai_enriched", self.lead._fields)
        self.assertIn("ai_source_text", self.lead._fields)


class TestCrmLeadAIWizardExtended(TransactionCase):
    """Extended tests for full branch coverage of CrmLeadAIWizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", "gemini")
        ICP.set_param("xtendoo_ai_connector.ai_api_key", "fake-key")
        ICP.set_param("xtendoo_ai_connector.ai_model", "gemini-2.5-flash")
        cls.lead = cls.env["crm.lead"].create({"name": "Extended Test Lead"})

    def _make_wizard(self, text="Some contact text"):
        return self.env["crm.lead.ai.wizard"].create(
            {"lead_id": self.lead.id, "source_text": text}
        )

    def _patch_provider(self, response_text):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = response_text
        return patch(
            "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
            ".CrmLeadAIWizard._get_ai_provider",
            return_value=mock_provider,
        )

    # --- action_analyze branches ---

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_analyze_ai_exception_raises_userror(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.side_effect = Exception("timeout")
        mock_get_provider.return_value = mock_provider

        with self.assertRaises(UserError) as ctx:
            self._make_wizard().action_analyze()
        self.assertIn("timeout", str(ctx.exception))

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_analyze_invalid_json_raises_userror(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = "not json {broken"
        mock_get_provider.return_value = mock_provider

        with self.assertRaises(UserError):
            self._make_wizard().action_analyze()

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_analyze_json_in_markdown_block(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = (
            "```json\n"
            '{"contact_name": "Ana", "email": "ana@test.es",'
            ' "company_name": null, "phone": null, "description": "test"}\n'
            "```"
        )
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.preview_contact_name, "Ana")
        self.assertEqual(wizard.preview_email, "ana@test.es")

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_analyze_bare_json_regex_fallback(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = (
            "Here is the data: "
            '{"contact_name": "Pedro", "email": null,'
            ' "company_name": "Test SL", "phone": null, "description": "d"}'
        )
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.preview_contact_name, "Pedro")
        self.assertEqual(wizard.preview_company_name, "Test SL")

    # --- action_apply branches ---

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_does_not_overwrite_all_existing_fields(self, mock_get_provider):
        lead = self.env["crm.lead"].create(
            {
                "name": "Overwrite Test",
                "email_from": "original@test.es",
                "phone": "+34600000000",
            }
        )
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": "New Name",
                "email": "new@test.es",
                "phone": "+34999999999",
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "0",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        # Existing fields preserved
        self.assertEqual(lead.email_from, "original@test.es")
        self.assertEqual(lead.phone, "+34600000000")

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_appends_notes_to_existing_description(self, mock_get_provider):
        lead = self.env["crm.lead"].create(
            {"name": "Notes Test", "description": "Existing description."}
        )
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": "AI summary",
                "tags": [],
                "priority": "0",
                "notes": "Urgent delivery needed.",
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        self.assertIn("Existing description.", lead.description)
        self.assertIn("Urgent delivery needed.", lead.description)
        self.assertIn("---", lead.description)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_no_notes_does_not_change_description(self, mock_get_provider):
        lead = self.env["crm.lead"].create(
            {"name": "No Notes Test", "description": "Keep this."}
        )
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "0",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        self.assertEqual(lead.description, "Keep this.")

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_tags_existing_tag_reused(self, mock_get_provider):
        existing_tag = self.env["crm.tag"].create({"name": "logistics-unique-9821"})
        lead = self.env["crm.lead"].create({"name": "Tag Reuse Test"})
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": ["logistics-unique-9821"],
                "priority": "0",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        tag_ids = lead.tag_ids.ids
        self.assertIn(existing_tag.id, tag_ids)
        # No duplicate created
        count = self.env["crm.tag"].search_count(
            [("name", "=", "logistics-unique-9821")]
        )
        self.assertEqual(count, 1)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_new_tag_created(self, mock_get_provider):
        lead = self.env["crm.lead"].create({"name": "New Tag Test"})
        tag_name = "brand-new-sector-tag-78291"
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [tag_name],
                "priority": "0",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        tag = self.env["crm.tag"].search([("name", "=", tag_name)], limit=1)
        self.assertTrue(tag)
        self.assertIn(tag.id, lead.tag_ids.ids)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_expected_revenue_written_when_empty(self, mock_get_provider):
        lead = self.env["crm.lead"].create({"name": "Revenue Test"})
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "expected_revenue": 25000.0,
                "priority": "0",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        self.assertAlmostEqual(float(lead.expected_revenue), 25000.0)

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_priority_written(self, mock_get_provider):
        lead = self.env["crm.lead"].create({"name": "Priority Test"})
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "2",
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        wizard.action_apply()

        self.assertEqual(lead.priority, "2")

    @patch(
        "odoo.addons.xtendoo_crm_ai.wizards.crm_lead_ai_wizard"
        ".CrmLeadAIWizard._get_ai_provider"
    )
    def test_apply_null_fields_do_not_crash(self, mock_get_provider):
        lead = self.env["crm.lead"].create({"name": "Null Fields Test"})
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = json.dumps(
            {
                "contact_name": None,
                "company_name": None,
                "email": None,
                "phone": None,
                "mobile": None,
                "website": None,
                "description": None,
                "tags": [],
                "expected_revenue": None,
                "priority": None,
                "notes": None,
            }
        )
        mock_get_provider.return_value = mock_provider

        wizard = self.env["crm.lead.ai.wizard"].create(
            {"lead_id": lead.id, "source_text": "text"}
        )
        wizard.action_analyze()
        # Must not raise
        wizard.action_apply()
        self.assertTrue(lead.ai_enriched)

    # --- CrmLead model ---

    def test_action_open_ai_enrichment_wizard_returns_act_window(self):
        lead = self.env["crm.lead"].create({"name": "Wizard Action Test"})
        result = lead.action_open_ai_enrichment_wizard()
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "crm.lead.ai.wizard")
        self.assertEqual(result["context"]["default_lead_id"], lead.id)

    def test_ai_enriched_default_false(self):
        lead = self.env["crm.lead"].create({"name": "Default AI Fields"})
        self.assertFalse(lead.ai_enriched)
        self.assertFalse(lead.ai_source_text)

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

        cls.lead = cls.env["crm.lead"].create({"name": "Test Lead", "type": "lead"})

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
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_action_analyze_sets_preview_state(self, mock_extract):
        mock_extract.return_value = json.loads(AI_CRM_RESPONSE)

        wizard = self._make_wizard("I need a warehouse solution")
        result = wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertEqual(wizard.preview_contact_name, "María García")
        self.assertEqual(wizard.preview_email, "maria@distribuciones.es")
        self.assertTrue(wizard.ai_json_result)
        self.assertFalse(self.lead.email_from)
        self.assertEqual(self.lead.type, "lead")
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "crm.lead.ai.wizard")
        self.assertEqual(result["res_id"], wizard.id)

    @patch(
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_action_analyze_empty_ai_response_raises(self, mock_extract):
        mock_extract.side_effect = UserError("empty response")

        wizard = self._make_wizard("Some text")
        with self.assertRaises(UserError):
            wizard.action_analyze()

    def test_action_apply_without_analyze_raises(self):
        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard.action_apply()

    @patch(
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_full_flow_analyze_and_apply(self, mock_extract):
        mock_extract.return_value = json.loads(AI_CRM_RESPONSE)

        wizard = self._make_wizard("Contact: María García, company: Distribuciones SL")
        wizard.action_analyze()
        result = wizard.action_apply()

        self.assertEqual(self.lead.email_from, "maria@distribuciones.es")
        self.assertEqual(self.lead.phone, "+34 612 345 678")
        self.assertTrue(self.lead.ai_enriched)
        self.assertTrue(self.lead.ai_source_text)
        self.assertEqual(self.lead.type, "lead")
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "crm.lead")
        self.assertEqual(result["res_id"], self.lead.id)
        self.assertEqual(result["context"]["default_type"], "lead")

    @patch(
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_apply_does_not_overwrite_existing_fields(self, mock_extract):
        """Apply should NOT overwrite fields that already have data."""
        self.lead.write({"email_from": "existing@email.com"})
        mock_extract.return_value = json.loads(AI_CRM_RESPONSE)

        wizard = self._make_wizard("Some text")
        wizard.action_analyze()
        wizard.action_apply()

        # Original email must be preserved
        self.assertEqual(self.lead.email_from, "existing@email.com")
        self.assertEqual(self.lead.type, "lead")

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
        cls.lead = cls.env["crm.lead"].create({"name": "Extended Test Lead", "type": "lead"})

    def _make_wizard(self, text="Some contact text"):
        return self.env["crm.lead.ai.wizard"].create(
            {"lead_id": self.lead.id, "source_text": text}
        )

    def _make_preview_wizard(self, lead=None, ai_data=None, text="text"):
        lead = lead or self.lead
        ai_data = ai_data or {}
        return self.env["crm.lead.ai.wizard"].create(
            {
                "lead_id": lead.id,
                "source_text": text,
                "ai_json_result": json.dumps(ai_data),
                "state": "preview",
            }
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
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_analyze_ai_exception_raises_userror(self, mock_extract):
        mock_extract.side_effect = UserError("timeout")

        with self.assertRaises(UserError) as ctx:
            self._make_wizard().action_analyze()
        self.assertIn("timeout", str(ctx.exception))

    def test_ai_parse_response_invalid_json_raises_userror(self):
        with self.assertRaises(UserError):
            self.lead._ai_parse_response("not json {broken")

    def test_ai_parse_response_json_in_markdown_block(self):
        result = self.lead._ai_parse_response(
            "```json\n"
            '{"contact_name": "Ana", "email": "ana@test.es",'
            ' "company_name": null, "phone": null, "description": "test"}\n'
            "```"
        )
        self.assertEqual(result["contact_name"], "Ana")
        self.assertEqual(result["email"], "ana@test.es")

    def test_ai_parse_response_bare_json_regex_fallback(self):
        result = self.lead._ai_parse_response(
            "Here is the data: "
            '{"contact_name": "Pedro", "email": null,'
            ' "company_name": "Test SL", "phone": null, "description": "d"}'
        )
        self.assertEqual(result["contact_name"], "Pedro")
        self.assertEqual(result["company_name"], "Test SL")

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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": "New Name",
                "email": "new@test.es",
                "phone": "+34999999999",
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "0",
                "notes": None,
            },
        )
        wizard.action_apply()

        # Existing fields preserved
        self.assertEqual(lead.email_from, "original@test.es")
        self.assertEqual(lead.phone, "+34600000000")
        self.assertEqual(lead.type, "lead")

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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": "AI summary",
                "tags": [],
                "priority": "0",
                "notes": "Urgent delivery needed.",
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "0",
                "notes": None,
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": ["logistics-unique-9821"],
                "priority": "0",
                "notes": None,
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [tag_name],
                "priority": "0",
                "notes": None,
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "expected_revenue": 25000.0,
                "priority": "0",
                "notes": None,
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
                "contact_name": None,
                "email": None,
                "phone": None,
                "company_name": None,
                "description": None,
                "tags": [],
                "priority": "2",
                "notes": None,
            },
        )
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

        wizard = self._make_preview_wizard(
            lead=lead,
            ai_data={
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
            },
        )
        # Must not raise
        wizard.action_apply()
        self.assertTrue(lead.ai_enriched)
        self.assertEqual(lead.type, "lead")

    def test_apply_on_existing_opportunity_keeps_opportunity_and_redirects(self):
        lead = self.env["crm.lead"].create(
            {"name": "Existing Opportunity", "type": "opportunity"}
        )
        wizard = self.env["crm.lead.ai.wizard"].create(
            {
                "lead_id": lead.id,
                "source_text": "text",
                "ai_json_result": json.dumps(
                    {
                        "contact_name": None,
                        "company_name": None,
                        "email": None,
                        "phone": None,
                        "description": None,
                        "tags": [],
                        "priority": None,
                        "notes": None,
                    }
                ),
                "state": "preview",
            }
        )

        result = wizard.action_apply()

        self.assertEqual(lead.type, "opportunity")
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_id"], lead.id)

    # --- CrmLead model ---

    def test_action_open_ai_enrichment_wizard_returns_act_window(self):
        lead = self.env["crm.lead"].create({"name": "Wizard Action Test"})
        result = lead.action_open_ai_enrichment_wizard()
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "crm.lead.ai.wizard")
        self.assertEqual(result["context"]["default_lead_id"], lead.id)

    def test_action_open_ai_enrichment_wizard_raises_if_already_enriched(self):
        lead = self.env["crm.lead"].create(
            {"name": "Already Enriched", "ai_enriched": True}
        )
        with self.assertRaises(UserError):
            lead.action_open_ai_enrichment_wizard()

    def test_ai_enriched_default_false(self):
        lead = self.env["crm.lead"].create({"name": "Default AI Fields"})
        self.assertFalse(lead.ai_enriched)
        self.assertFalse(lead.ai_source_text)

    @patch(
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_message_new_auto_enriches_incoming_email_lead(self, mock_extract):
        mock_extract.return_value = {
            "contact_name": "Jenna",
            "company_name": "Conet Plastic",
            "email": "jenna@conetplastic.com",
            "phone": "19026809628",
            "description": "PVC strip door factory asking for a quotation.",
            "tags": ["pvc", "strip curtain"],
            "priority": "0",
            "notes": "Preferred contact via email.",
        }

        lead = self.env["crm.lead"].message_new(
            {
                "subject": "Solicitud de presupuesto",
                "email_from": "Jenna <jenna@conetplastic.com>",
                "from": "Jenna <jenna@conetplastic.com>",
                "to": "ventas@doorme.com",
                "cc": "",
                "recipients": "ventas@doorme.com",
                "date": "2026-04-28 10:00:00",
                "body": "<p>Our company is the pvc strip door factory.</p>",
            },
            custom_values={"type": "lead"},
        )

        self.assertEqual(lead.type, "lead")
        self.assertTrue(lead.ai_enriched)
        self.assertEqual(lead.partner_name, "Conet Plastic")
        self.assertEqual(lead.phone, "19026809628")
        self.assertIn("Subject: Solicitud de presupuesto", lead.ai_source_text)
        self.assertIn("Body:", lead.ai_source_text)

    @patch(
        "odoo.addons.xtendoo_crm_ai.models.crm_lead.CrmLead._ai_extract_data_from_text"
    )
    def test_message_new_ai_failure_does_not_block_lead_creation(self, mock_extract):
        mock_extract.side_effect = UserError("provider error")

        lead = self.env["crm.lead"].message_new(
            {
                "subject": "Incoming lead",
                "email_from": "sender@example.com",
                "from": "sender@example.com",
                "to": "ventas@doorme.com",
                "cc": "",
                "recipients": "ventas@doorme.com",
                "date": "2026-04-28 10:00:00",
                "body": "<p>Hello</p>",
            },
            custom_values={"type": "lead"},
        )

        self.assertTrue(lead)
        self.assertEqual(lead.type, "lead")
        self.assertFalse(lead.ai_enriched)


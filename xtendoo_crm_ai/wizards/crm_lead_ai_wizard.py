# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CrmLeadAIWizard(models.TransientModel):
    _name = "crm.lead.ai.wizard"
    _description = "AI Enrichment Wizard for CRM Leads"
    _inherit = "xtendoo.ai.connector.mixin"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead / Opportunity",
        required=True,
        ondelete="cascade",
    )
    source_text = fields.Text(
        string="Text to Analyze",
        required=True,
        help=(
            "Paste here the form submission, email, chat transcript or any text "
            "from which the AI should extract lead information."
        ),
    )
    state = fields.Selection(
        selection=[
            ("draft", "Enter Text"),
            ("preview", "Review & Apply"),
        ],
        default="draft",
    )
    ai_json_result = fields.Text(string="AI JSON Result", readonly=True)

    # Preview fields (readonly, shown before applying)
    preview_contact_name = fields.Char(string="Contact Name", readonly=True)
    preview_company_name = fields.Char(string="Company", readonly=True)
    preview_email = fields.Char(string="Email", readonly=True)
    preview_phone = fields.Char(string="Phone", readonly=True)
    preview_description = fields.Text(string="AI Summary", readonly=True)

    def action_analyze(self):
        """Send source text to AI and preview results."""
        self.ensure_one()
        ai_data = self.lead_id._ai_extract_data_from_text(self.source_text)

        self.write(
            {
                "ai_json_result": json.dumps(ai_data, ensure_ascii=False, indent=2),
                "preview_contact_name": ai_data.get("contact_name") or "",
                "preview_company_name": ai_data.get("company_name") or "",
                "preview_email": ai_data.get("email") or "",
                "preview_phone": ai_data.get("phone") or "",
                "preview_description": self._build_preview_description(ai_data),
                "state": "preview",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead.ai.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply(self):
        """Apply AI-extracted data to the lead and close the wizard."""
        self.ensure_one()

        if not self.ai_json_result:
            raise UserError(_("Please analyze text first."))

        ai_data = json.loads(self.ai_json_result or "{}")
        self.lead_id._ai_apply_data(ai_data, source_text=self.source_text, overwrite=True)
        return self.lead_id.redirect_lead_opportunity_view()

    def _build_preview_description(self, ai_data: dict) -> str:
        """Build a rich preview description from all AI-extracted fields."""
        parts = []
        if ai_data.get("description"):
            parts.append(ai_data["description"])
        products = ai_data.get("products_or_services") or []
        if products:
            parts.append("Products/Services: " + ", ".join(products))
        if ai_data.get("inquiry_type"):
            parts.append("Inquiry type: " + ai_data["inquiry_type"])
        if ai_data.get("preferred_contact_channel"):
            parts.append("Preferred contact: " + ai_data["preferred_contact_channel"])
        if ai_data.get("preferred_contact_time"):
            parts.append("Preferred time: " + ai_data["preferred_contact_time"])
        certs = ai_data.get("certifications") or []
        if certs:
            parts.append("Certifications: " + ", ".join(certs))
        if ai_data.get("notes"):
            parts.append("Notes: " + ai_data["notes"])
        return "\n".join(parts)

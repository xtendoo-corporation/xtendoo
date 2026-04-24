# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CRM_EXTRACTION_PROMPT = """
You are an expert CRM analyst. The following text comes from a web contact form,
an email, a chat transcript, or any free-form inquiry from a potential customer or supplier.
Your task is to extract every piece of information that can enrich a CRM lead record.

Return ONLY a valid JSON object with this exact structure (no markdown, no extra text):

{
  "lead_name": "<short descriptive title for this lead, e.g. subject line or 'Inquiry from <company>', or null>",
  "contact_name": "<full name of the contact person, or null>",
  "job_position": "<job title or role of the contact person, or null>",
  "company_name": "<company or organization name, or null>",
  "company_type": "<manufacturer|distributor|retailer|agency|freelance|other, or null>",
  "email": "<email address, or null>",
  "phone": "<phone number, or null>",
  "mobile": "<mobile number if different from phone, or null>",
  "website": "<company website URL, or null>",
  "source_url": "<URL of the web page or form from which the message was sent, or null>",
  "street": "<street address, or null>",
  "city": "<city, or null>",
  "zip": "<postal code, or null>",
  "country_name": "<country name in English, or null>",
  "lang": "<ISO 639-1 language code of the message, e.g. en, es, fr, zh, de, or null>",
  "preferred_contact_channel": "<email|phone|whatsapp|other, or null>",
  "preferred_contact_time": "<preferred time or time range to contact, e.g. '15:00-17:00', or null>",
  "subject": "<email or form subject line, or null>",
  "products_or_services": ["<product or service 1>", "<product or service 2>"],
  "certifications": ["<certification 1>"],
  "inquiry_type": "<quote_request|product_info|partnership|complaint|support|other>",
  "expected_revenue": <estimated deal value as a float if mentioned, or null>,
  "description": "<neutral 2-3 sentence summary of what the contact is asking for or offering>",
  "tags": ["<business sector tag>", "<product/service tag>"],
  "priority": "<0|1|2|3 — 0=normal, 1=low, 2=high, 3=very high>",
  "notes": "<verbatim extra details not captured in other fields: contact preferences, conditions, observations>"
}

Extraction rules:
- Extract ONLY what is explicitly stated or strongly implied. Do NOT invent data.
- Use null for any field not found in the text.
- lead_name: use the subject line if present; otherwise synthesize a short title from company + intent.
- company_type: infer from context clues (e.g. "factory" → manufacturer, "distributor" mentioned, etc.).
- lang: detect the language the message body is written in.
- preferred_contact_channel: extract from phrases like "via email", "call me", "WhatsApp", etc.
- preferred_contact_time: extract time ranges or indications like "15:00-17:00", "mornings", etc.
- products_or_services: list every product, service or product category explicitly mentioned.
- certifications: list any quality/compliance certificates mentioned (REACH, ISO, CE, etc.).
- inquiry_type: classify the intent — quote_request if they ask for a price/budget, etc.
- tags: use 2-5 short lowercase tags reflecting industry and product interest.
- priority: 1 if urgency/deadline mentioned; 2 if large budget; 3 if both; 0 otherwise.
- notes: capture contact preferences, schedules, specific conditions, or any verbatim detail not elsewhere.

TEXT TO ANALYZE:
"""


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

        if not self.source_text or not self.source_text.strip():
            raise UserError(_("Please enter some text to analyze."))

        ai_provider = self._get_ai_provider()
        full_prompt = CRM_EXTRACTION_PROMPT + self.source_text.strip()

        try:
            raw_text = ai_provider.send_prompt(full_prompt)
        except Exception as exc:
            _logger.error("AI enrichment failed: %s", exc, exc_info=True)
            raise UserError(_("AI analysis failed: %s") % str(exc)) from exc

        if not raw_text:
            raise UserError(_("The AI returned an empty response."))

        clean = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
        if clean:
            raw_text = clean.group(1)
        else:
            clean = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            if clean:
                raw_text = clean.group(1)

        try:
            ai_data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise UserError(
                _("Could not parse AI response as JSON: %s\n\nRaw response:\n%s")
                % (str(exc), raw_text[:500])
            ) from exc

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
        """Apply AI-extracted data to the lead."""
        self.ensure_one()

        if not self.ai_json_result:
            raise UserError(_("Please analyze text first."))

        ai_data = json.loads(self.ai_json_result)
        lead = self.lead_id

        update_vals = {}

        # Lead title
        if ai_data.get("lead_name") and not lead.name or lead.name == _("New"):
            update_vals["name"] = ai_data["lead_name"]

        # Contact & company
        if ai_data.get("contact_name") and not lead.contact_name:
            update_vals["contact_name"] = ai_data["contact_name"]
        if ai_data.get("job_position") and not lead.function:
            update_vals["function"] = ai_data["job_position"]
        if ai_data.get("company_name") and not lead.partner_name:
            update_vals["partner_name"] = ai_data["company_name"]
        if ai_data.get("email") and not lead.email_from:
            update_vals["email_from"] = ai_data["email"]
        if ai_data.get("phone") and not lead.phone:
            update_vals["phone"] = ai_data["phone"]
        if ai_data.get("mobile") and not lead.mobile:
            update_vals["mobile"] = ai_data["mobile"]
        if ai_data.get("website") and not lead.website:
            update_vals["website"] = ai_data["website"]

        # Address
        if ai_data.get("street") and not lead.street:
            update_vals["street"] = ai_data["street"]
        if ai_data.get("city") and not lead.city:
            update_vals["city"] = ai_data["city"]
        if ai_data.get("zip") and not lead.zip:
            update_vals["zip"] = ai_data["zip"]
        if ai_data.get("country_name") and not lead.country_id:
            country = self.env["res.country"].search(
                [("name", "ilike", ai_data["country_name"])], limit=1
            )
            if country:
                update_vals["country_id"] = country.id

        # Revenue & priority
        if ai_data.get("expected_revenue") and not lead.expected_revenue:
            update_vals["expected_revenue"] = float(ai_data["expected_revenue"])
        if ai_data.get("priority") is not None:
            update_vals["priority"] = str(ai_data["priority"])

        # Tags: sector + products + inquiry_type + certifications
        tag_names = list(ai_data.get("tags") or [])
        if ai_data.get("inquiry_type"):
            tag_names.append(ai_data["inquiry_type"].replace("_", " "))
        if ai_data.get("company_type"):
            tag_names.append(ai_data["company_type"])
        for cert in ai_data.get("certifications") or []:
            tag_names.append(cert)
        if tag_names:
            tags = self.env["crm.tag"]
            for tag_name in tag_names:
                tag = tags.search([("name", "ilike", tag_name)], limit=1)
                if not tag:
                    tag = tags.create({"name": tag_name})
                tags |= tag
            existing_tags = lead.tag_ids
            update_vals["tag_ids"] = [(4, t.id) for t in tags if t not in existing_tags]

        # Build rich description from AI summary + structured data
        description_parts = []
        if ai_data.get("description"):
            description_parts.append(ai_data["description"])
        products = ai_data.get("products_or_services") or []
        if products:
            description_parts.append(
                _("Products / Services: %s") % ", ".join(products)
            )
        if ai_data.get("subject"):
            description_parts.append(_("Subject: %s") % ai_data["subject"])
        if ai_data.get("source_url"):
            description_parts.append(_("Source page: %s") % ai_data["source_url"])
        if ai_data.get("lang"):
            description_parts.append(_("Message language: %s") % ai_data["lang"])
        if ai_data.get("preferred_contact_channel"):
            description_parts.append(
                _("Preferred contact: %s") % ai_data["preferred_contact_channel"]
            )
        if ai_data.get("preferred_contact_time"):
            description_parts.append(
                _("Preferred time: %s") % ai_data["preferred_contact_time"]
            )
        if ai_data.get("notes"):
            description_parts.append(_("Notes: %s") % ai_data["notes"])

        if description_parts:
            existing = lead.description or ""
            separator = "\n\n---\n" if existing else ""
            update_vals["description"] = existing + separator + "\n".join(description_parts)

        update_vals["ai_enriched"] = True
        update_vals["ai_source_text"] = self.source_text

        lead.write(update_vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI Enrichment Applied"),
                "message": _(
                    "Lead '%s' has been enriched with AI-extracted data."
                ) % lead.name,
                "type": "success",
                "sticky": False,
            },
        }

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

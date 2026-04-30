# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.translate import _

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
- lead_name: use the subject line if present; otherwise synthesize a short title from company + contact person + intent. If the subject is very generic (e.g., "Inquiry", "Hello", "Presupuesto"), append the contact name or company to it (e.g., "Presupuesto - Juan Pérez").
- contact_name: extract the full name of the contact person. Look for it in greetings, signatures (e.g., "Saludos, [Nombre]"), or explicit form fields in the body. Prioritize this over the name in the email header.
- company_type: infer from context clues (e.g. "factory" → manufacturer, "distributor" mentioned, etc.).
- lang: detect the language the message body is written in.
- preferred_contact_channel: extract from phrases like "via email", "call me", "WhatsApp", etc.
- preferred_contact_time: extract time ranges or indications like "15:00-17:00", "mornings", etc.
- products_or_services: list every product, service or product category explicitly mentioned.
- certifications: list any quality/compliance certificates mentioned (REACH, ISO, CE, etc.).
- inquiry_type: classify the intent — quote_request if they ask for a price/budget, etc.
- tags: use 2-5 short lowercase tags reflecting industry and product interest.
- If the text is an email and the body contains contact information (contact_name, email, phone, etc.) that differs from the email headers (From, etc.), prioritize the information in the body.
- priority: 1 if urgency/deadline mentioned; 2 if large budget; 3 if both; 0 otherwise.
- notes: capture contact preferences, schedules, specific conditions, or any verbatim detail not elsewhere.

TEXT TO ANALYZE:
"""


class CrmLead(models.Model):
    _inherit = "crm.lead"

    ai_enriched = fields.Boolean(
        string="Enriched by AI",
        default=False,
        copy=False,
        help="Indicates this lead has been enriched with AI-extracted data.",
    )
    ai_source_text = fields.Text(
        string="AI Source Text",
        copy=False,
        help="Original text used by AI to enrich this lead.",
    )

    @api.model
    def _ai_build_source_text_from_message(self, msg_dict):
        """Build normalized text from an incoming email payload for AI analysis."""
        body = tools.html2plaintext(msg_dict.get("body") or "")
        parts = []
        for label, key in (
            ("From", "email_from"),
            ("To", "to"),
            ("Cc", "cc"),
            ("Subject", "subject"),
            ("Date", "date"),
        ):
            value = (msg_dict.get(key) or "").strip()
            if value:
                parts.append(f"{label}: {value}")
        if body.strip():
            parts.append("")
            parts.append("Body:")
            parts.append(body.strip())
        return "\n".join(parts).strip()

    @api.model
    def _ai_parse_response(self, raw_text):
        """Parse the provider raw response into a JSON dict."""
        clean = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
        if clean:
            raw_text = clean.group(1)
        else:
            clean = re.search(r"({.*})", raw_text, re.DOTALL)
            if clean:
                raw_text = clean.group(1)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise UserError(
                _("Could not parse AI response as JSON: %s\n\nRaw response:\n%s")
                % (str(exc), raw_text[:500])
            ) from exc

    @api.model
    def _ai_extract_data_from_text(self, source_text):
        """Run the CRM extraction prompt against the configured AI provider."""
        source_text = (source_text or "").strip()
        if not source_text:
            raise UserError(_("Please enter some text to analyze."))

        ai_provider = self.env["xtendoo.ai.connector.mixin"]._get_ai_provider()
        full_prompt = CRM_EXTRACTION_PROMPT + source_text

        try:
            raw_text = ai_provider.send_prompt(full_prompt)
        except Exception as exc:
            _logger.error("AI enrichment failed: %s", exc, exc_info=True)
            raise UserError(_("AI analysis failed: %s") % str(exc)) from exc

        if not raw_text:
            raise UserError(_("The AI returned an empty response."))

        return self._ai_parse_response(raw_text)

    def _ai_apply_data(self, ai_data, source_text=None, overwrite=False):
        """Apply AI-extracted CRM data.
        If overwrite is True, it will replace existing values.
        Otherwise, it only fills empty fields.
        """
        self.ensure_one()
        lead = self
        update_vals = {}

        if ai_data.get("lead_name") and (overwrite or not lead.name or lead.name == _("New")):
            update_vals["name"] = ai_data["lead_name"]

        if ai_data.get("contact_name") and (overwrite or not lead.contact_name):
            update_vals["contact_name"] = ai_data["contact_name"]
        if ai_data.get("job_position") and (overwrite or not lead.function):
            update_vals["function"] = ai_data["job_position"]
        if ai_data.get("company_name") and (overwrite or not lead.partner_name):
            update_vals["partner_name"] = ai_data["company_name"]
        if ai_data.get("email") and (overwrite or not lead.email_from):
            update_vals["email_from"] = ai_data["email"]
        if ai_data.get("phone") and (overwrite or not lead.phone):
            update_vals["phone"] = ai_data["phone"]
        if ai_data.get("mobile") and (overwrite or not lead.mobile):
            update_vals["mobile"] = ai_data["mobile"]
        if ai_data.get("website") and (overwrite or not lead.website):
            update_vals["website"] = ai_data["website"]

        if ai_data.get("street") and (overwrite or not lead.street):
            update_vals["street"] = ai_data["street"]
        if ai_data.get("city") and (overwrite or not lead.city):
            update_vals["city"] = ai_data["city"]
        if ai_data.get("zip") and (overwrite or not lead.zip):
            update_vals["zip"] = ai_data["zip"]
        if ai_data.get("country_name") and (overwrite or not lead.country_id):
            country = self.env["res.country"].search(
                [("name", "ilike", ai_data["country_name"])], limit=1
            )
            if country:
                update_vals["country_id"] = country.id

        if ai_data.get("expected_revenue") and (overwrite or not lead.expected_revenue):
            update_vals["expected_revenue"] = float(ai_data["expected_revenue"])
        if ai_data.get("priority") is not None and (overwrite or not lead.priority or lead.priority == "0"):
            update_vals["priority"] = str(ai_data["priority"])

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
        if source_text is not None:
            update_vals["ai_source_text"] = source_text

        lead.write(update_vals)
        return update_vals

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Auto-enrich leads created from incoming emails using the email content."""
        lead = super().message_new(msg_dict, custom_values=custom_values)
        source_text = self._ai_build_source_text_from_message(msg_dict)
        if not source_text:
            return lead

        try:
            ai_data = lead._ai_extract_data_from_text(source_text)
            lead._ai_apply_data(ai_data, source_text=source_text, overwrite=True)
        except UserError as exc:
            _logger.warning(
                "AI auto-enrichment skipped for incoming lead %s: %s",
                lead.id,
                exc,
            )
        except Exception:
            _logger.exception(
                "Unexpected AI auto-enrichment error for incoming lead %s",
                lead.id,
            )
        return lead

    def action_open_ai_enrichment_wizard(self):
        """Open the AI enrichment wizard for this lead."""
        self.ensure_one()
        if self.ai_enriched:
            raise UserError(_("This lead has already been enriched by AI."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Enrich Lead with AI"),
            "res_model": "crm.lead.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lead_id": self.id},
        }

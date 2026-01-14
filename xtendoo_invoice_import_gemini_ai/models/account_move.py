# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import re
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None


class AccountMove(models.Model):
    _inherit = "account.move"

    gemini_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Gemini Attachment",
        help="Attachment to be processed by Gemini AI",
        copy=False,
    )

    def action_import_gemini_full(self):
        """Import invoice details with Gemini AI including all lines."""
        return self._process_with_gemini(summary_mode=False)

    def action_import_gemini_summarized(self):
        """Import invoice details with Gemini AI summarized by VAT type."""
        return self._process_with_gemini(summary_mode=True)

    def _process_with_gemini(self, summary_mode=False):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("You can only import AI data on draft invoices."))
        if self.move_type != "in_invoice":
            raise UserError(_("AI import is only available for vendor bills."))

        # 1. Get attachment
        attachment = self._get_ai_attachment()
        if not attachment:
            raise UserError(
                _("Please attach a PDF or image file to this invoice first.")
            )

        # 2. Setup Gemini
        api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_import_gemini_ai.gemini_api_key")
        )
        if not api_key:
            raise UserError(
                _(
                    "Gemini API Key not configured. Please go to Settings → Accounting → Gemini AI."
                )
            )

        model_name = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "xtendoo_invoice_import_gemini_ai.gemini_model", "gemini-2.0-flash-exp"
            )
        )

        if not genai or not types:
            raise UserError(_("google-genai library is not installed. Please install it with: pip install google-genai"))

        # Usar la nueva API con Client
        client = genai.Client(api_key=api_key)

        # 3. Prepare data for Gemini
        file_content = base64.b64decode(attachment.datas)
        mime_type = attachment.mimetype

        prompt = self._get_gemini_prompt(summary_mode=summary_mode)

        try:
            # Preparar el archivo con la nueva API
            file_part = types.Part.from_bytes(
                data=file_content,
                mime_type=mime_type
            )

            # Generar contenido con la nueva API
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, file_part]
            )

            if not response or not response.text:
                raise UserError(_("Gemini AI returned an empty response."))

            # Clean response text (sometimes it includes ```json ... ``` blocks)
            raw_text = response.text
            json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if json_match:
                raw_text = json_match.group(1)
            else:
                # Try to find anything that looks like JSON
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if json_match:
                    raw_text = json_match.group(1)

            ai_data = json.loads(raw_text)

            # 4. Apply data
            self._apply_gemini_data(ai_data, summary_mode=summary_mode)

            self.message_post(
                body=_(
                    "✅ Invoice data successfully imported from Gemini AI (%s mode)!"
                )
                % (_("Full") if not summary_mode else _("Summarized")),
                attachments=[(attachment.name, attachment.datas)],
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Invoice data imported successfully!"),
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            }

        except Exception as e:
            _logger.error(f"Gemini AI error: {str(e)}", exc_info=True)
            raise UserError(_("Error processing with Gemini AI: %s") % str(e))

    def _get_ai_attachment(self):
        """Find the attachment to process."""
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "account.move"),
                ("res_id", "=", self.id),
                (
                    "mimetype",
                    "in",
                    ["application/pdf", "image/jpeg", "image/png", "image/jpg"],
                ),
            ],
            limit=1,
            order="create_date desc",
        )
        return attachments[0] if attachments else None

    def _get_gemini_prompt(self, summary_mode=False):
        """Get the prompt for Gemini AI."""
        prompt = """Extract all data from this invoice and return it in JSON format.
Required structure:
{
    "supplier": {
        "name": "Supplier company name",
        "vat": "Tax ID/VAT number",
        "address": "Full address"
    },
    "invoice": {
        "number": "Invoice number",
        "date": "YYYY-MM-DD",
        "due_date": "YYYY-MM-DD or null",
        "currency": "EUR/USD/etc"
    },
    "lines": [
        {
            "description": "Short description",
            "quantity": 1.0,
            "unit_price": 100.00,
            "tax_percent": 21.0
        }
    ],
    "totals": {
        "untaxed": 100.00,
        "tax": 21.00,
        "total": 121.00
    }
}
"""
        if summary_mode:
            prompt += "\nIMPORTANT: In 'lines', please group all items by their VAT percentage. Return only one line per VAT group with the total amount for that group. Use a generic description like 'Goods/Services at X% VAT'."
        else:
            prompt += "\nIMPORTANT: Extract ALL individual line items from the invoice."

        prompt += "\nIdentify tax rates correctly (e.g., 21, 10, 4, 0). Return ONLY the JSON object."
        return prompt

    def _apply_gemini_data(self, data, summary_mode=False):
        """Apply extracted data to the invoice."""
        self.ensure_one()

        supplier_data = data.get("supplier", {})
        invoice_data = data.get("invoice", {})
        lines_data = data.get("lines", [])

        # 1. Partner
        partner = self._find_partner(supplier_data)
        if partner:
            self.partner_id = partner
            self._onchange_partner_id()

        # 2. Header
        if invoice_data.get("number"):
            self.ref = invoice_data["number"]
        if invoice_data.get("date"):
            self.invoice_date = invoice_data["date"]
        if invoice_data.get("due_date"):
            self.invoice_date_due = invoice_data["due_date"]

        if invoice_data.get("currency"):
            currency = self.env["res.currency"].search(
                [("name", "=", invoice_data["currency"].upper())], limit=1
            )
            if currency:
                self.currency_id = currency

        # 3. Lines
        # Remove existing lines first
        self.invoice_line_ids = [(5, 0, 0)]

        lines_to_create = []
        default_account = self._get_default_expense_account()

        for line in lines_data:
            tax_percent = line.get("tax_percent")
            tax = self._find_tax(tax_percent)

            line_vals = {
                "name": line.get("description", "Imported line"),
                "quantity": line.get("quantity", 1.0),
                "price_unit": line.get("unit_price", 0.0),
                "account_id": default_account.id if default_account else False,
                "tax_ids": [(6, 0, [tax.id])] if tax else [],
            }
            lines_to_create.append((0, 0, line_vals))

        self.invoice_line_ids = lines_to_create

        # Trigger recomputation of taxes and totals
        self._recompute_dynamic_lines()

    def _find_partner(self, supplier_data):
        vat = supplier_data.get("vat")
        name = supplier_data.get("name")

        if vat:
            vat_clean = re.sub(r"[^A-Z0-9]", "", vat.upper())
            partner = self.env["res.partner"].search(
                ["|", ("vat", "=", vat), ("vat", "=", vat_clean)], limit=1
            )
            if partner:
                return partner

        if name:
            partner = self.env["res.partner"].search([("name", "ilike", name)], limit=1)
            if partner:
                return partner

        return None

    def _find_tax(self, percent):
        if percent is None:
            return None
        return self.env["account.tax"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", float(percent)),
            ],
            limit=1,
        )

    def _get_default_expense_account(self):
        journal = self.journal_id
        if journal and journal.default_account_id:
            return journal.default_account_id

        return self.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

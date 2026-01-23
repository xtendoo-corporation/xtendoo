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
    gemini_auto_processed = fields.Boolean(
        string="Auto Processed by Gemini",
        help="Indicates if this invoice was automatically processed by Gemini AI",
        default=False,
        copy=False,
    )

    @api.model
    def create(self, vals):
        """Override create to trigger auto scan after creation if attachment is present."""
        move = super(AccountMove, self).create(vals)
        if move.move_type == 'in_invoice' and move.state == 'draft':
            move._auto_scan_if_configured()
        return move

    def write(self, vals):
        """Override write to trigger auto scan when attachments change."""
        res = super(AccountMove, self).write(vals)
        # Check if we should trigger auto scan
        # We trigger on message_main_attachment_id changes or when invoices become draft
        if 'message_main_attachment_id' in vals or 'state' in vals:
            for move in self:
                if move.move_type == 'in_invoice' and move.state == 'draft':
                    move._auto_scan_if_configured()
        return res

    def _auto_scan_if_configured(self):
        """Automatically scan invoice if auto scan is enabled and conditions are met."""
        self.ensure_one()

        # Don't process if already processed or if not a draft vendor bill
        if self.gemini_auto_processed or self.state != 'draft' or self.move_type != 'in_invoice':
            return

        # Check if there are any invoice lines already (don't overwrite existing data)
        if self.invoice_line_ids:
            return

        # Get auto scan configuration
        auto_scan_mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_import_gemini_ai.gemini_auto_scan", "disabled")
        )

        if auto_scan_mode == 'disabled':
            return

        # Check if there's an attachment to process
        attachment = self._get_ai_attachment()
        if not attachment:
            return

        # Process with Gemini AI
        try:
            summary_mode = (auto_scan_mode == 'summary')
            _logger.info(f"Auto-scanning invoice {self.id} with mode: {auto_scan_mode}")
            self._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
            self.gemini_auto_processed = True
        except Exception as e:
            # Log error but don't fail the invoice creation/update
            _logger.warning(
                f"Auto-scan failed for invoice {self.id}: {str(e)}. "
                "User can still manually trigger the scan."
            )

    def action_import_gemini_full(self):
        """Import invoice details with Gemini AI including all lines."""
        return self._process_with_gemini(summary_mode=False)

    def action_import_gemini_summarized(self):
        """Import invoice details with Gemini AI summarized by VAT type."""
        return self._process_with_gemini(summary_mode=True)

    def _process_with_gemini(self, summary_mode=False, auto_mode=False):
        self.ensure_one()
        if self.state != "draft":
            if not auto_mode:
                raise UserError(_("You can only import AI data on draft invoices."))
            return
        if self.move_type != "in_invoice":
            if not auto_mode:
                raise UserError(_("AI import is only available for vendor bills."))
            return

        # 1. Get attachment
        attachment = self._get_ai_attachment()
        if not attachment:
            if not auto_mode:
                raise UserError(
                    _("Please attach a PDF or image file to this invoice first.")
                )
            return

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
                "xtendoo_invoice_import_gemini_ai.gemini_model", "gemini-2.5-flash"
            )
        )

        # Limpiar el nombre del modelo si viene con prefijo "models/"
        if model_name and model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        # Validar modelos obsoletos y sugerir alternativas
        obsolete_models = {
            "gemini-pro": "gemini-2.5-flash",
            "gemini-pro-vision": "gemini-2.5-flash",
            "gemini-1.5-pro": "gemini-2.5-pro",
            "gemini-1.5-flash": "gemini-2.5-flash",
            "gemini-1.5-flash-002": "gemini-2.5-flash",
            "gemini-1.5-pro-002": "gemini-2.5-pro",
            "gemini-2.0-flash-exp": "gemini-2.5-flash",
        }
        if model_name in obsolete_models:
            suggested_model = obsolete_models[model_name]
            raise UserError(
                _(
                    "The model '%s' is obsolete or not available. "
                    "Please update your configuration to use '%s' or another available model. "
                    "Recommended models: gemini-2.5-flash (fast), gemini-2.5-pro (high quality), "
                    "gemini-flash-latest, gemini-pro-latest. "
                    "Go to Settings → Accounting → Gemini AI to update the model and use "
                    "'Test Gemini Connection' to see all available models."
                ) % (model_name, suggested_model)
            )

        if not genai or not types:
            raise UserError(_("google-genai library is not installed. Please install it with: pip install google-genai"))

        # Usar la nueva API con Client
        client = genai.Client(api_key=api_key)

        _logger.info(f"Using Gemini model: {model_name}")

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

            # Post message only if not in auto mode
            if not auto_mode:
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
            else:
                # In auto mode, just log success
                _logger.info(
                    f"Invoice {self.id} automatically processed with Gemini AI "
                    f"({'Full' if not summary_mode else 'Summarized'} mode)"
                )

        except Exception as e:
            _logger.error(f"Gemini AI error: {str(e)}", exc_info=True)
            if not auto_mode:
                raise UserError(_("Error processing with Gemini AI: %s") % str(e))
            else:
                # In auto mode, just log the error and continue
                _logger.warning(
                    f"Auto-scan failed for invoice {self.id}: {str(e)}"
                )

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
            # Trigger onchange to update fields like payment terms, fiscal position, etc.
            # In Odoo 19, onchange methods are triggered automatically in form views,
            # but when setting values programmatically, we may need to trigger them manually
            if hasattr(self, '_onchange_partner_id'):
                try:
                    self._onchange_partner_id()
                except Exception as e:
                    _logger.warning(f"Could not trigger partner onchange: {str(e)}")
        else:
            vals_partner = {
                "name": supplier_data.get("name", "Unknown Supplier"),
                "vat": supplier_data.get("vat", False),
                "street": supplier_data.get("address", False),
                "supplier_rank": 1,
            }
            new_partner = self.env["res.partner"].create(vals_partner)
            self.partner_id = new_partner
            if hasattr(self, '_onchange_partner_id'):
                try:
                    self._onchange_partner_id()
                except Exception as e:
                    _logger.warning(f"Could not trigger partner onchange: {str(e)}")

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

        # In Odoo 19, taxes and totals are automatically recomputed through computed fields
        # when invoice lines are modified, so no manual trigger is needed

    def _find_partner(self, supplier_data):
        vat = supplier_data.get("vat")
        name = supplier_data.get("name")
        print("*"*50)
        print("Finding partner with VAT:", vat, "or Name:", name)
        print("*"*50)

        if vat:
            vat_clean = re.sub(r"[^A-Z0-9]", "", vat.upper())
            vat_clean = (vat_clean or "").strip().upper()
            partner = self.env["res.partner"].sudo().search(
                [("vat", "ilike", vat_clean)],
                limit=1
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

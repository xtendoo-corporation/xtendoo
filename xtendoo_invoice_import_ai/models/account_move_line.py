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
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None


class AccountMoveLine(models.Model):
    _inherit = ["account.move.line", "xtendoo.ai.connector.mixin"]

    gemini_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Gemini Attachment",
        help="Attachment to be processed by Gemini AI",
        copy=False,
    )
    gemini_auto_processed = fields.Boolean(
        string="Auto Processed by Gemini",
        help="Indicates if this entry was automatically processed by Gemini AI",
        default=False,
        copy=False,
    )
    parent_state = fields.Selection(
        related="move_id.state",
        string="Parent State",
        store=False,
        readonly=True,
    )

    @api.model
    def create(self, vals):
        """Override create to trigger auto scan after creation if attachment is present."""
        line = super(AccountMoveLine, self).create(vals)
        if line.move_id and line.move_id.state == 'draft':
            _logger.info(f"Line {line.id} created in draft move, checking for auto scan...")
            line._auto_scan_if_configured()
        return line

    def _auto_scan_if_configured(self):
        """Automatically scan entry if auto scan is enabled and conditions are met."""
        self.ensure_one()

        # Don't process if already processed or if not a draft document
        if self.gemini_auto_processed or self.move_id.state != 'draft':
            return

        # Check if there are any invoice lines already (don't overwrite existing data)
        if len(self.move_id.line_ids) > 1:  # More than just this line
            return

        # Get auto scan configuration
        auto_scan_mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_import_ai.gemini_auto_scan", "disabled")
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
            _logger.info(f"Auto-scanning entry line {self.id} with mode: {auto_scan_mode}")
            self._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
            self.gemini_auto_processed = True
        except Exception as e:
            # Log error but don't fail the entry creation/update
            _logger.warning(
                f"Auto-scan failed for entry line {self.id}: {str(e)}. "
                "User can still manually trigger the scan."
            )

    def action_import_gemini_full(self):
        """Import entry details with Gemini AI including all lines."""
        return self._process_with_gemini(summary_mode=False)

    def action_import_gemini_summarized(self):
        """Import entry details with Gemini AI summarized by VAT type."""
        return self._process_with_gemini(summary_mode=True)

    def _process_with_gemini(self, summary_mode=False, auto_mode=False):
        self.ensure_one()

        move = self.move_id
        if not move:
            if not auto_mode:
                raise UserError(_("This line is not associated with any journal entry."))
            return

        if move.state != "draft":
            if not auto_mode:
                raise UserError(_("You can only import AI data on draft entries."))
            return

        # 1. Get attachment
        attachment = self._get_ai_attachment()
        if not attachment:
            if not auto_mode:
                raise UserError(
                    _("Please attach a PDF or image file to this entry first.")
                )
            return

        # 2. Build AI provider from global connector configuration
        ai_provider = self._get_ai_provider()

        # 3. Prepare data for AI
        file_content = base64.b64decode(attachment.datas)
        mime_type = attachment.mimetype

        prompt = self._get_gemini_prompt(summary_mode=summary_mode)

        try:
            raw_text = ai_provider.send_prompt(
                prompt,
                files=[{"data": file_content, "mime_type": mime_type}],
            )

            if not raw_text:
                raise UserError(_("The AI returned an empty response."))

            # Clean response text (sometimes it includes ```json ... ``` blocks)
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
                move.message_post(
                    body=_(
                        "✅ Entry data successfully imported from Gemini AI (%s mode)!"
                    )
                    % (_("Full") if not summary_mode else _("Summarized")),
                    attachments=[(attachment.name, attachment.datas)],
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": _("Entry data imported successfully!"),
                        "type": "success",
                        "sticky": False,
                        "next": {"type": "ir.actions.client", "tag": "reload"},
                    },
                }
            else:
                # In auto mode, just log success
                _logger.info(
                    f"Entry line {self.id} automatically processed with Gemini AI "
                    f"({'Full' if not summary_mode else 'Summarized'} mode)"
                )

        except Exception as e:
            _logger.error(f"Gemini AI error: {str(e)}", exc_info=True)
            if not auto_mode:
                raise UserError(_("Error processing with Gemini AI: %s") % str(e))
            else:
                # In auto mode, just log the error and continue
                _logger.warning(
                    f"Auto-scan failed for entry line {self.id}: {str(e)}"
                )

    def _get_ai_attachment(self):
        """Find the attachment to process."""
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "account.move.line"),
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
        if not attachments and self.move_id:
            # If no attachment on line, try to get from move
            attachments = self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", self.move_id.id),
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
        prompt = """Extract all data from this document and return it in JSON format.
Required structure:
{
    "supplier": {
        "name": "Supplier company name",
        "vat": "Tax ID/VAT number",
        "address": "Full address"
    },
    "invoice": {
        "number": "Invoice/Document number",
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
            prompt += "\nIMPORTANT: Extract ALL individual line items from the document."

        prompt += "\nIdentify tax rates correctly (e.g., 21, 10, 4, 0). Return ONLY the JSON object."
        return prompt

    def _apply_gemini_data(self, data, summary_mode=False):
        """Apply extracted data to the entry."""
        self.ensure_one()

        move = self.move_id
        if not move:
            raise UserError(_("This line is not associated with any journal entry."))

        supplier_data = data.get("supplier", {})
        invoice_data = data.get("invoice", {})
        lines_data = data.get("lines", [])

        # 1. Partner
        partner = self._find_partner(supplier_data)
        if partner:
            move.partner_id = partner
        else:
            vals_partner = {
                "name": supplier_data.get("name", "Unknown Supplier"),
                "vat": supplier_data.get("vat", False),
                "street": supplier_data.get("address", False),
                "supplier_rank": 1,
            }
            new_partner = self.env["res.partner"].create(vals_partner)
            move.partner_id = new_partner

        # 2. Header
        if invoice_data.get("number"):
            move.ref = invoice_data["number"]
        if invoice_data.get("date"):
            move.date = invoice_data["date"]

        if invoice_data.get("currency"):
            currency = self.env["res.currency"].search(
                [("name", "=", invoice_data["currency"].upper())], limit=1
            )
            if currency:
                move.currency_id = currency

        # 3. Lines
        # Remove existing lines first (except this one if it exists)
        existing_lines = move.line_ids.filtered(lambda l: l.id != self.id)
        existing_lines.unlink()

        lines_to_create = []
        default_account = self._get_default_account()

        for line in lines_data:
            tax_percent = line.get("tax_percent")
            tax = self._find_tax(tax_percent)

            # Create debit line (expense/asset)
            line_vals = {
                "move_id": move.id,
                "name": line.get("description", "Imported line"),
                "quantity": line.get("quantity", 1.0),
                "price_unit": line.get("unit_price", 0.0),
                "account_id": default_account.id if default_account else False,
                "tax_ids": [(6, 0, [tax.id])] if tax else [],
                "debit": line.get("quantity", 1.0) * line.get("unit_price", 0.0),
                "credit": 0.0,
            }
            lines_to_create.append(line_vals)

        # Create all lines
        for line_vals in lines_to_create:
            self.env["account.move.line"].create(line_vals)

        # Get payable account for credit line
        payable_account = self._get_payable_account(partner)

        # Calculate total and create credit line (payable)
        total_debit = sum(line.get("quantity", 1.0) * line.get("unit_price", 0.0) for line in lines_data)

        credit_line_vals = {
            "move_id": move.id,
            "name": invoice_data.get("number", "Payable"),
            "account_id": payable_account.id if payable_account else False,
            "partner_id": partner.id if partner else False,
            "debit": 0.0,
            "credit": total_debit,
        }
        self.env["account.move.line"].create(credit_line_vals)

    def _find_partner(self, supplier_data):
        vat = supplier_data.get("vat")
        name = supplier_data.get("name")
        _logger.info(f"Finding partner with VAT: {vat} or Name: {name}")

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
                ("company_id", "=", self.move_id.company_id.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", float(percent)),
            ],
            limit=1,
        )

    def _get_default_account(self):
        """Get default expense account."""
        move = self.move_id
        if move and move.journal_id and move.journal_id.default_account_id:
            return move.journal_id.default_account_id

        return self.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_id", "=", move.company_id.id if move else self.env.company.id),
            ],
            limit=1,
        )

    def _get_payable_account(self, partner):
        """Get payable account for partner."""
        if partner and partner.property_account_payable_id:
            return partner.property_account_payable_id

        return self.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", self.move_id.company_id.id if self.move_id else self.env.company.id),
            ],
            limit=1,
        )

    @api.model
    def create_document_from_attachment(self, attachment_ids=None):
        """
        Create account.move from attachment(s) when uploading from journal items list.
        Called by the file uploader component.
        Creates a new journal entry and processes it with Gemini AI.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided."))

        # Get journal from context or use default general journal
        journal_id = self.env.context.get('default_journal_id')
        if not journal_id:
            # Get the default general journal for the company
            company_id = self.env.company.id
            journal = self.env['account.journal'].search(
                [
                    ('type', '=', 'general'),
                    ('company_id', '=', company_id),
                ],
                limit=1,
            )
            if not journal:
                raise UserError(
                    _("No general journal found for company %s. Please create one.") % self.env.company.name
                )
            journal_id = journal.id

        # Create moves from attachments
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        created_lines = self.env['account.move.line']

        for attachment in attachments:
            # Create journal entry
            move_vals = {
                'journal_id': journal_id,
                'state': 'draft',
                'date': fields.Date.context_today(self),
            }
            move = self.env['account.move'].create(move_vals)

            # Link attachment to the move
            attachment.write({
                'res_model': 'account.move',
                'res_id': move.id,
            })

            # Create a placeholder line to trigger the processing
            line_vals = {
                'move_id': move.id,
                'name': 'Processing...',
                'account_id': self._get_default_account().id,
                'debit': 0.0,
                'credit': 0.0,
            }
            line = self.create(line_vals)
            created_lines |= line

            _logger.info(f"Created line {line.id} in move {move.id} from attachment {attachment.id}")

            # Process with Gemini AI if auto_scan is enabled
            auto_scan_mode = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("xtendoo_invoice_import_ai.gemini_auto_scan", "disabled")
            )

            if auto_scan_mode != 'disabled':
                try:
                    summary_mode = (auto_scan_mode == 'summary')
                    _logger.info(f"Processing line {line.id} with Gemini AI ({auto_scan_mode} mode)")
                    line._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
                    line.gemini_auto_processed = True
                    _logger.info(f"Line {line.id} successfully processed by Gemini AI")
                except Exception as e:
                    _logger.warning(f"Failed to process line {line.id} with Gemini AI: {str(e)}")

        # Return action to open the first created move
        if created_lines:
            move = created_lines[0].move_id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journal Entry'),
                'res_model': 'account.move',
                'res_id': move.id,
                'views': [[self.env.ref('account.view_move_form').id, 'form']],
                'target': 'current',
            }

        return {'type': 'ir.actions.client', 'tag': 'reload'}


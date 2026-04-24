# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import re

from odoo import _, fields, models
from odoo.tools.translate import _lt
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    import io
except ImportError:
    convert_from_bytes = None
    Image = None
    io = None

DOCUMENT_TYPE_LABELS = {
    "salary": _lt("Payslip / Salary"),
    "expense": _lt("Expense"),
    "income": _lt("Income"),
    "other": _lt("Other"),
}

PROMPTS = {
    "detect": """
You are an expert accountant. Analyze the attached document and return ONLY a JSON object
with the following structure (no markdown, no extra text):

{
  "document_type": "<salary|expense|income|other>",
  "document_type_reason": "<brief explanation of why you chose this type>",
  "supplier": {
    "name": "<supplier or employer name>",
    "vat": "<VAT number if found, else null>"
  },
  "date": "<YYYY-MM-DD or null>",
  "reference": "<document reference/number or null>",
  "currency": "<ISO code, e.g. EUR>",
  "journal_lines": [
    {
      "account_code": "<PGC account code>",
      "account_name": "<descriptive name>",
      "description": "<line description>",
      "debit": <float>,
      "credit": <float>
    }
  ],
  "totals": {
    "subtotal": <float>,
    "tax_amount": <float>,
    "total": <float>
  }
}

Rules:
- document_type must be one of: salary, expense, income, other
- For salary: use PGC accounts 640x (gross salary), 476x (social security payable),
  642x (social security company), 465x (net salary payable)
- For expense: use PGC accounts 6xxx (expenses) and 472x (deductible VAT)
- For income: use PGC accounts 7xxx (revenues) and 477x (VAT collected)
- journal_lines must balance: sum(debit) == sum(credit)
- All amounts must be positive floats
""",
}


class AccountMoveAIWizard(models.TransientModel):
    _name = "account.move.ai.wizard"
    _description = "AI Document Import Wizard for Journal Entries"
    _inherit = "xtendoo.ai.connector.mixin"

    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        required=True,
        ondelete="cascade",
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Document",
        help="PDF or image of the document to analyze (invoice, payslip, expense receipt, etc.)",
    )
    detected_document_type = fields.Selection(
        selection=[
            ("salary", "Payslip / Salary"),
            ("expense", "Expense"),
            ("income", "Income"),
            ("other", "Other"),
        ],
        string="Detected Document Type",
        readonly=True,
    )
    detected_reason = fields.Char(string="Detection Reason", readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Upload Document"),
            ("preview", "Review & Confirm"),
        ],
        default="draft",
        string="State",
    )
    ai_json_result = fields.Text(string="AI JSON Result", readonly=True)

    def _get_ai_provider(self):
        """Delegate to the AI connector mixin. Defined here to allow patching in tests."""
        return super()._get_ai_provider()

    def action_analyze(self):
        """Send the document to AI for analysis."""
        self.ensure_one()

        if not self.attachment_id:
            raise UserError(_("Please attach a document before analyzing."))

        ai_provider = self._get_ai_provider()

        file_content = base64.b64decode(self.attachment_id.datas)
        mime_type = self.attachment_id.mimetype or "application/pdf"

        # Convert PDF first page to image for better AI compatibility
        files = self._prepare_files(file_content, mime_type)

        try:
            raw_text = ai_provider.send_prompt(PROMPTS["detect"], files=files)
        except Exception as exc:
            _logger.error("AI analysis failed: %s", exc, exc_info=True)
            raise UserError(
                _("AI analysis failed: %s") % str(exc)
            ) from exc

        if not raw_text:
            raise UserError(_("The AI returned an empty response."))

        # Clean JSON from markdown code blocks
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
                "detected_document_type": ai_data.get("document_type", "other"),
                "detected_reason": ai_data.get("document_type_reason", ""),
                "ai_json_result": json.dumps(ai_data, ensure_ascii=False, indent=2),
                "state": "preview",
            }
        )
        # Refresh the wizard form
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.ai.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply(self):
        """Apply AI-extracted data to the journal entry."""
        self.ensure_one()

        if not self.ai_json_result:
            raise UserError(_("Please analyze a document first."))

        ai_data = json.loads(self.ai_json_result)
        move = self.move_id

        if move.state != "draft":
            raise UserError(_("Journal entry must be in draft state to apply AI data."))

        self._apply_to_move(move, ai_data)

        move.write(
            {
                "ai_document_type": ai_data.get("document_type", "other"),
                "ai_processed": True,
                "ai_has_corrections": False,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI Import Successful"),
                "message": _(
                    "Document processed as '%s'. Journal entry has been populated."
                ) % (ai_data.get("document_type", "other")),
                "type": "success",
                "sticky": False,
            },
        }

    def _prepare_files(self, file_content: bytes, mime_type: str) -> list:
        """
        Prepare file list for AI provider.
        Converts PDF first page to PNG for better compatibility when possible.
        """
        if mime_type == "application/pdf" and convert_from_bytes and Image and io:
            try:
                images = convert_from_bytes(file_content, first_page=1, last_page=1, dpi=200)
                if images:
                    buf = io.BytesIO()
                    images[0].save(buf, format="PNG")
                    return [{"data": buf.getvalue(), "mime_type": "image/png"}]
            except Exception as exc:
                _logger.warning("PDF to image conversion failed, sending raw PDF: %s", exc)
        return [{"data": file_content, "mime_type": mime_type}]

    def _apply_to_move(self, move, ai_data: dict):
        """
        Apply AI-extracted data to the journal entry.
        Creates journal lines from ai_data['journal_lines'].
        """
        # Remove existing lines
        move.line_ids.unlink()

        # Update move header
        date_str = ai_data.get("date")
        if date_str:
            try:
                from datetime import date
                parsed_date = date.fromisoformat(date_str)
                move.write({"invoice_date": parsed_date, "date": parsed_date})
            except ValueError:
                _logger.warning("Could not parse date '%s' from AI response", date_str)

        ref = ai_data.get("reference")
        if ref:
            move.write({"ref": ref})

        # Resolve partner
        supplier = ai_data.get("supplier", {})
        partner = self._find_partner(supplier)
        if partner:
            move.write({"partner_id": partner.id})

        # Create journal lines
        lines_data = ai_data.get("journal_lines", [])
        line_vals = []
        for line in lines_data:
            account = self._find_or_create_account(
                line.get("account_code", ""), line.get("account_name", "")
            )
            if not account:
                _logger.warning(
                    "Could not find account '%s' - skipping line", line.get("account_code")
                )
                continue
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "account_id": account.id,
                        "name": line.get("description", ""),
                        "debit": float(line.get("debit", 0.0)),
                        "credit": float(line.get("credit", 0.0)),
                        "partner_id": partner.id if partner else False,
                    },
                )
            )

        if line_vals:
            move.write({"line_ids": line_vals})

    def _find_partner(self, supplier: dict):
        """Search for a partner by VAT or name."""
        if not supplier:
            return None
        vat = supplier.get("vat")
        name = supplier.get("name")
        Partner = self.env["res.partner"]
        if vat:
            partner = Partner.search([("vat", "=", vat)], limit=1)
            if partner:
                return partner
        if name:
            partner = Partner.search([("name", "ilike", name)], limit=1)
            if partner:
                return partner
        return None

    def _find_or_create_account(self, code: str, name: str):
        """Find an account by code; log a warning if not found (no auto-creation)."""
        if not code:
            return None
        account = self.env["account.account"].search(
            [("code", "=like", code + "%")], limit=1
        )
        if not account:
            _logger.warning(
                "Account with code '%s' (%s) not found in chart of accounts.", code, name
            )
            return None
        return account

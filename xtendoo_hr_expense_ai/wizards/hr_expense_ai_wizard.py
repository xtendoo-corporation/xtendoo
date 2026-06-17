# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import json
import logging
import re
from odoo import models, fields, _
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
PROMPTS = {
    "detect": """
You are an expert assistant for expense management. Analyze the attached receipt/document and return ONLY a JSON object
with the following structure (no markdown, no extra text):
{
  "document_type": "expense",
  "document_type_reason": "<brief explanation>",
  "supplier": {
    "name": "<supplier name>",
    "vat": "<VAT number if found, else null>"
  },
  "date": "<YYYY-MM-DD or null>",
  "description": "<detailed description of the expense>",
  "currency": "<ISO code, e.g. EUR>",
  "total_amount": <float>,
  "tax_amount": <float>,
  "product_hint": "<suggested type of expense: e.g. Meals, Travel, Supplies, Fuel>"
}
""",
}
class HrExpenseAIWizard(models.TransientModel):
    _name = "hr.expense.ai.wizard"
    _description = "AI Document Import Wizard for HR Expenses"
    _inherit = "xtendoo.ai.connector.mixin"
    expense_id = fields.Many2one(
        "hr.expense",
        string="Expense",
        required=True,
        ondelete="cascade",
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Document",
        help="PDF or image of the receipt to analyze.",
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
        return super()._get_ai_provider()
    def action_analyze(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("Please attach a document before analyzing."))
        ai_provider = self._get_ai_provider()
        file_content = base64.b64decode(self.attachment_id.datas)
        mime_type = self.attachment_id.mimetype or "application/pdf"
        files = self._prepare_files(file_content, mime_type)
        try:
            raw_text = ai_provider.send_prompt(PROMPTS["detect"], files=files)
        except Exception as exc:
            _logger.error("AI analysis failed: %s", exc, exc_info=True)
            raise UserError(_("AI analysis failed: %s") % str(exc)) from exc
        if not raw_text:
            raise UserError(_("The AI returned an empty response."))
        clean = re.search(r"\`\`\`json\s*(.*?)\s*\`\`\`", raw_text, re.DOTALL)
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
        self.write({
            "detected_reason": ai_data.get("document_type_reason", ""),
            "ai_json_result": json.dumps(ai_data, ensure_ascii=False, indent=2),
            "state": "preview",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.expense.ai.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
    def action_apply(self):
        self.ensure_one()
        if not self.ai_json_result:
            raise UserError(_("Please analyze a document first."))
        ai_data = json.loads(self.ai_json_result)
        expense = self.expense_id
        self._apply_to_expense(expense, ai_data)
        expense.write({
            "ai_document_type": ai_data.get("document_type", "expense"),
            "ai_processed": True,
            "ai_has_corrections": False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI Import Successful"),
                "message": _("Expense data has been populated from the document."),
                "type": "success",
                "sticky": False,
            },
        }
    def _prepare_files(self, file_content: bytes, mime_type: str) -> list:
        if mime_type == "application/pdf" and convert_from_bytes and Image and io:
            try:
                images = convert_from_bytes(file_content, first_page=1, last_page=1, dpi=200)
                if images:
                    buf = io.BytesIO()
                    images[0].save(buf, format="PNG")
                    return [{"data": buf.getvalue(), "mime_type": "image/png"}]
            except Exception as exc:
                _logger.warning("PDF to image conversion failed: %s", exc)
        return [{"data": file_content, "mime_type": mime_type}]
    def _apply_to_expense(self, expense, ai_data: dict):
        vals = {}
        # Date
        date_str = ai_data.get("date")
        if date_str:
            try:
                from datetime import date
                vals["date"] = date.fromisoformat(date_str)
            except ValueError:
                pass
        # Description
        desc = ai_data.get("description")
        if desc:
            vals["name"] = desc
        # Amount
        total = ai_data.get("total_amount")
        if total:
            vals["total_amount_currency"] = float(total)
        # Currency
        currency_code = ai_data.get("currency")
        if currency_code:
            currency = self.env["res.currency"].search([("name", "=", currency_code)], limit=1)
            if currency:
                vals["currency_id"] = currency.id
        # Try to find a product based on hint or description
        product_hint = ai_data.get("product_hint", "")
        if product_hint:
            product = self.env["product.product"].search([
                ("can_be_expensed", "=", True),
                "|", ("name", "ilike", product_hint), ("default_code", "ilike", product_hint)
            ], limit=1)
            if product:
                vals["product_id"] = product.id
        if vals:
            expense.write(vals)
        # Handle attachment linkage if not already linked
        if self.attachment_id:
            self.attachment_id.write({
                "res_model": "hr.expense",
                "res_id": expense.id,
            })

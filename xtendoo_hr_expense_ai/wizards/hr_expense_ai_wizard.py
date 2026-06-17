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
Eres un experto asistente contable para la gestión de gastos en España. Analiza el documento adjunto y devuelve ÚNICAMENTE un objeto JSON
con la siguiente estructura (sin markdown, sin texto adicional):

{
  "document_type": "expense",
  "document_type_reason": "<explicación breve en español de por qué elegiste este tipo>",
  "supplier": {
    "name": "<nombre del proveedor>",
    "vat": "<CIF/NIF del proveedor si lo encuentras, si no null>"
  },
  "date": "<YYYY-MM-DD o null>",
  "description": "<descripción detallada del gasto en español>",
  "currency": "<código ISO, ej. EUR>",
  "total_amount": <float>,
  "tax_amount": <float>,
  "product_hint": "<tipo de gasto sugerido en español: ej. Comidas, Viajes, Suministros, Combustible>"
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
    attachment_file = fields.Binary(
        string="Documento",
        required=True,
        help="Sube el PDF o imagen del ticket/factura para analizar.",
    )
    attachment_name = fields.Char(string="Nombre del archivo")
    detected_reason = fields.Char(string="Razón de Detección", readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Subir Documento"),
            ("preview", "Revisar y Confirmar"),
        ],
        default="draft",
        string="Estado",
    )
    ai_json_result = fields.Text(string="Resultado JSON de IA", readonly=True)
    def _get_ai_provider(self):
        return super()._get_ai_provider()
    def action_analyze(self):
        self.ensure_one()
        if not self.attachment_file:
            raise UserError(_("Por favor, adjunte un documento antes de analizar."))
        ai_provider = self._get_ai_provider()
        file_content = base64.b64decode(self.attachment_file)
        mime_type = "application/pdf"
        if self.attachment_name:
            import mimetypes
            mime_type = mimetypes.guess_type(self.attachment_name)[0] or mime_type
        files = self._prepare_files(file_content, mime_type)
        try:
            raw_text = ai_provider.send_prompt(PROMPTS["detect"], files=files)
        except Exception as exc:
            _logger.error("AI analysis failed: %s", exc, exc_info=True)
            raise UserError(_("AI analysis failed: %s") % str(exc)) from exc
        if not raw_text:
            raise UserError(_("La IA devolvió una respuesta vacía."))
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
                _("No se pudo procesar la respuesta de la IA como JSON: %s\n\nRespuesta original:\n%s")
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
            raise UserError(_("Por favor, analice un documento primero."))
        ai_data = json.loads(self.ai_json_result)
        expense = self.expense_id
        self._apply_to_expense(expense, ai_data)
        self.env["ir.attachment"].create({
            "name": self.attachment_name or "expense_receipt",
            "datas": self.attachment_file,
            "res_model": "hr.expense",
            "res_id": expense.id,
        })
        expense.write({
            "ai_document_type": ai_data.get("document_type", "expense"),
            "ai_processed": True,
            "ai_has_corrections": False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Importación IA Exitosa"),
                "message": _("Los datos del gasto se han rellenado desde el documento."),
                "type": "success",
                "sticky": False,
            },
        }
    def _apply_to_expense(self, expense, ai_data: dict):
        vals = {}
        date_str = ai_data.get("date")
        if date_str:
            try:
                from datetime import date
                vals["date"] = date.fromisoformat(date_str)
            except ValueError:
                pass
        desc = ai_data.get("description")
        if desc:
            vals["name"] = desc
        total = ai_data.get("total_amount")
        if total:
            vals["total_amount_currency"] = float(total)
        currency_code = ai_data.get("currency")
        if currency_code:
            currency = self.env["res.currency"].search([("name", "=", currency_code)], limit=1)
            if currency:
                vals["currency_id"] = currency.id
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

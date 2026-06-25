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
        required=False,
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
        # Get expensable products as categories
        expensable_products = self.env["product.product"].search([("can_be_expensed", "=", True)])
        categories_str = ", ".join([f'"{p.name}"' for p in expensable_products])
        prompt = PROMPTS["detect"]
        if categories_str:
            prompt += f"\nLas categorías de gasto válidas en nuestro sistema son únicamente las siguientes: [{categories_str}]. Por favor, selecciona la que mejor se adapte al gasto analizado y devuélvela exactamente en el campo 'product_hint'."

        try:
            raw_text = ai_provider.send_prompt(prompt, files=files)
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
        created_new = False
        if not expense:
            employee = self.env.user.employee_id
            if not employee:
                employee = self.env["hr.employee"].search([("user_id", "=", self.env.uid)], limit=1)
            if not employee:
                employee = self.env["hr.employee"].search([("company_id", "=", (self.env.company or self.env.user.company_id).id)], limit=1)

            expense_vals = {
                "name": ai_data.get("description") or "Nuevo Gasto IA",
            }
            if employee:
                expense_vals["employee_id"] = employee.id

            expense = self.env["hr.expense"].with_context(skip_compute_tax_ids=True).create(expense_vals)
            created_new = True

        self._apply_to_expense(expense, ai_data)

        if not expense.product_id:
            fallback_product = self.env["product.product"].search([
                ("can_be_expensed", "=", True)
            ], limit=1)
            if fallback_product:
                expense.with_context(skip_compute_tax_ids=True).product_id = fallback_product.id

        self.env["ir.attachment"].create({
            "name": self.attachment_name or "expense_receipt",
            "datas": self.attachment_file,
            "res_model": "hr.expense",
            "res_id": expense.id,
        })
        expense.with_context(skip_compute_tax_ids=True).write({
            "ai_document_type": ai_data.get("document_type", "expense"),
            "ai_processed": True,
            "ai_has_corrections": False,
        })

        if created_new:
            return {
                "name": _("Gasto Importado"),
                "type": "ir.actions.act_window",
                "res_model": "hr.expense",
                "res_id": expense.id,
                "view_mode": "form",
                "target": "current",
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Importación IA Exitosa"),
                    "message": _("Los datos del gasto se han rellenado desde el documento."),
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.client",
                        "tag": "reload",
                    },
                },
            }

    def _apply_to_expense(self, expense, ai_data: dict):
        vals = {
            "payment_mode": "company_account",
        }
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
                ("name", "=", product_hint)
            ], limit=1)
            if not product:
                product = self.env["product.product"].search([
                    ("can_be_expensed", "=", True),
                    "|", ("name", "ilike", product_hint), ("default_code", "ilike", product_hint)
                ], limit=1)
            if product:
                vals["product_id"] = product.id

        # Map Supplier/Vendor without creating res.partner
        supplier = ai_data.get("supplier")
        if supplier:
            name = supplier.get("name")
            vat = supplier.get("vat")
            partner = False
            if vat:
                clean_vat = re.sub(r'[^A-Z0-9]', '', vat.upper())
                partner = self.env["res.partner"].search([("vat", "=", vat)], limit=1)
                if not partner:
                    partner = self.env["res.partner"].search([("vat", "ilike", clean_vat)], limit=1)
            if not partner and name:
                partner = self.env["res.partner"].search([("name", "ilike", name)], limit=1)

            if partner:
                vals["vendor_id"] = partner.id
            else:
                notes = []
                if name:
                    notes.append(f"Proveedor Detectado: {name}")
                if vat:
                    notes.append(f"NIF/CIF Detectado: {vat}")
                if notes:
                    current_desc = expense.description or ""
                    new_notes = "\n".join(notes)
                    vals["description"] = f"{current_desc}\n\n{new_notes}".strip()

        # Map Taxes
        total_amount = ai_data.get("total_amount")
        tax_amount = ai_data.get("tax_amount")
        if total_amount and tax_amount:
            try:
                total_amount = float(total_amount)
                tax_amount = float(tax_amount)
                tax = False
                company = expense.company_id or self.env.company

                # Sort helper to find the standard tax
                def find_best_tax(rate):
                    taxes = self.env["account.tax"].search([
                        ("type_tax_use", "=", "purchase"),
                        ("amount", "=", rate),
                        ("company_id", "=", company.id),
                    ])
                    if not taxes:
                        taxes = self.env["account.tax"].search([
                            ("type_tax_use", "=", "purchase"),
                            ("amount", "=", round(rate)),
                            ("company_id", "=", company.id),
                        ])
                    if not taxes:
                        return False

                    def tax_sort_key(t):
                        name = (t.name or "").upper()
                        penalty = 0
                        if any(term in name for term in ["EX", "ISP", "RECARGO", "INTRA", "REVERSADO"]):
                            penalty += 100
                        if "S" in name or "SOPORTADO" in name:
                            penalty -= 10
                        return (penalty, len(name), t.id)

                    return sorted(taxes, key=tax_sort_key)[0]

                # Formula A: Tax Included
                untaxed_a = total_amount - tax_amount
                rate_a = 0.0
                rate_b = 0.0
                if untaxed_a > 0:
                    rate_a = round((tax_amount / untaxed_a) * 100, 1)
                    tax = find_best_tax(rate_a)

                # Formula B: Tax Excluded (fallback)
                if not tax and total_amount > 0:
                    rate_b = round((tax_amount / total_amount) * 100, 1)
                    tax = find_best_tax(rate_b)

                if not tax and (rate_a or rate_b):
                    target_rate = rate_a if rate_a > 0.0 else rate_b
                    if target_rate > 0.0:
                        tax = self.env["account.tax"].create({
                            "name": f"IVA Soportado {target_rate}%",
                            "amount": target_rate,
                            "type_tax_use": "purchase",
                            "company_id": company.id,
                        })

                if tax:
                    vals["tax_ids"] = [(6, 0, [tax.id])]
            except (ValueError, TypeError):
                pass

        if vals:
            expense.with_context(skip_compute_tax_ids=True).write(vals)
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

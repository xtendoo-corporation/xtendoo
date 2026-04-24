# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import re
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = ["account.analytic.line", "xtendoo.ai.connector.mixin"]

    gemini_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Gemini Attachment",
        help="Attachment to be processed by Gemini AI",
        copy=False,
    )
    gemini_auto_processed = fields.Boolean(
        string="Auto Processed by Gemini",
        help="Indicates if this analytic line was automatically processed by Gemini AI",
        default=False,
        copy=False,
    )

    # Tracking: valores que extrajo Gemini originalmente
    gemini_extracted_partner = fields.Char(string="Proveedor extraído por Gemini", copy=False)
    gemini_extracted_date = fields.Char(string="Fecha extraída por Gemini", copy=False)
    gemini_extracted_amount = fields.Float(string="Importe extraído por Gemini", copy=False)
    gemini_extracted_description = fields.Char(string="Descripción extraída por Gemini", copy=False)

    # Flag: se activa cuando Gemini procesa el apunte.
    # El usuario lo desactiva pulsando "Enseñar a Gemini" para confirmar que los datos son correctos.
    gemini_has_corrections = fields.Boolean(
        string="Pendiente de enseñar a Gemini",
        default=False,
        copy=False,
    )


    def action_teach_gemini(self):
        """Enseña a Gemini las correcciones manuales realizadas."""
        self.ensure_one()
        feedback_vals = {
            "source_model": "account.analytic.line",
            "analytic_line_id": self.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "gemini_partner_name": self.gemini_extracted_partner,
            "gemini_date": self.gemini_extracted_date,
            "gemini_amount": self.gemini_extracted_amount,
            "gemini_description": self.gemini_extracted_description,
            "correct_partner_name": self.partner_id.name if self.partner_id else False,
            "correct_date": str(self.date) if self.date else False,
            "correct_amount": self.amount,
            "correct_description": self.name,
        }
        self.env["gemini.feedback"].create(feedback_vals)
        self.gemini_has_corrections = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gemini aprendió"),
                "message": _("Las correcciones han sido guardadas. Gemini las usará en futuras extracciones."),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def create_document_from_attachment(self, name=None, attachment_ids=None):
        """
        Odoo uploader llama: create_document_from_attachment("", [ids])
        Crea un apunte analítico (account.analytic.line) y lo rellena con Gemini AI.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided."))

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        created_lines = self.env['account.analytic.line']

        auto_scan_mode = (
            self.env["ir.config_parameter"].sudo()
            .get_param("xtendoo_invoice_import_ai.gemini_auto_scan", "disabled")
        )
        summary_mode = (auto_scan_mode == 'summary')

        for attachment in attachments:
            # Crear apunte analítico vacío
            line = self.create({
                'name': attachment.name or _('Imported document'),
                'date': fields.Date.context_today(self),
                'amount': 0.0,
            })

            # Vincular adjunto al apunte
            attachment.write({
                'res_model': 'account.analytic.line',
                'res_id': line.id,
            })
            line.gemini_attachment_id = attachment.id
            created_lines |= line

            _logger.info(f"Created analytic line {line.id} from attachment {attachment.id}")

            # Procesar con Gemini AI
            # gemini_auto_processed=True se guarda dentro de _apply_gemini_data_to_line
            try:
                self._process_line_with_gemini(line, attachment, summary_mode=summary_mode)
            except Exception as e:
                _logger.warning(f"Gemini AI failed for line {line.id}: {e}")

        if created_lines:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Analytic Item'),
                'res_model': 'account.analytic.line',
                'res_id': created_lines[0].id,
                'views': [[False, 'form']],
                'target': 'current',
            }
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _process_line_with_gemini(self, line, attachment, summary_mode=False):
        """Rellena el apunte analítico con los datos extraídos por la IA."""
        ai_provider = self._get_ai_provider()

        file_content = base64.b64decode(attachment.datas)
        prompt = self._get_gemini_prompt(summary_mode=summary_mode)

        raw_text = ai_provider.send_prompt(
            prompt,
            files=[{"data": file_content, "mime_type": attachment.mimetype}],
        )

        if not raw_text:
            raise UserError(_("The AI returned an empty response."))

        m = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
        if m:
            raw_text = m.group(1)
        else:
            m = re.search(r"(\{.*})", raw_text, re.DOTALL)
            if m:
                raw_text = m.group(1)

        ai_data = json.loads(raw_text)
        self._apply_gemini_data_to_line(line, ai_data)
        _logger.info("Analytic line %s processed by AI OK", line.id)

    def _apply_gemini_data_to_line(self, line, data):
        """Aplica los datos de Gemini al apunte analítico y guarda los valores originales."""
        supplier_data = data.get("supplier", {})
        invoice_data = data.get("invoice", {})
        totals = data.get("totals", {})

        vals = {}
        amount = totals.get("untaxed") or totals.get("total") or 0.0

        if invoice_data.get("number"):
            vals['name'] = invoice_data["number"]
        if invoice_data.get("date"):
            vals['date'] = invoice_data["date"]
        if amount:
            vals['amount'] = -abs(float(amount))

        partner = self._find_partner(supplier_data)
        if not partner and supplier_data.get("name"):
            partner = self.env["res.partner"].create({
                "name": supplier_data.get("name"),
                "vat": supplier_data.get("vat", False),
                "supplier_rank": 1,
            })
        if partner:
            vals['partner_id'] = partner.id

        # Guardar valores originales y marcar como procesado en un único write
        # así el compute se dispara una sola vez con todos los datos disponibles
        vals['gemini_extracted_partner'] = supplier_data.get("name", "")
        vals['gemini_extracted_date'] = invoice_data.get("date", "")
        vals['gemini_extracted_amount'] = -abs(float(amount)) if amount else 0.0
        vals['gemini_extracted_description'] = invoice_data.get("number", "")
        vals['gemini_auto_processed'] = True
        vals['gemini_has_corrections'] = True  # Activar siempre al escanear

        if vals:
            line.write(vals)
        _logger.info(f"Applied Gemini data to analytic line {line.id}: {vals}")

    def _get_gemini_prompt(self, summary_mode=False, partner_id=None):
        """Get the prompt for Gemini AI, incluyendo feedback de correcciones anteriores."""
        # Contexto de correcciones anteriores
        feedback_context = self.env["gemini.feedback"].get_feedback_context_for_prompt(
            partner_id=partner_id
        )

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
        if feedback_context:
            prompt += feedback_context

        if summary_mode:
            prompt += "\nIMPORTANT: In 'lines', group all items by VAT percentage. One line per VAT group."
        else:
            prompt += "\nIMPORTANT: Extract ALL individual line items from the document."

        prompt += "\nIdentify tax rates correctly (e.g., 21, 10, 4, 0). Return ONLY the JSON object."
        return prompt

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

    def _find_tax(self, percent, company_id):
        if percent is None:
            return None
        return self.env["account.tax"].search(
            [
                ("company_id", "=", company_id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", float(percent)),
            ],
            limit=1,
        )

    def _get_default_account(self, move):
        """Get default expense account."""
        if move and move.journal_id and move.journal_id.default_account_id:
            return move.journal_id.default_account_id

        return self.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_id", "=", move.company_id.id if move else self.env.company.id),
            ],
            limit=1,
        )

    def _get_payable_account(self, partner, company_id):
        """Get payable account for partner."""
        if partner and partner.property_account_payable_id:
            return partner.property_account_payable_id

        return self.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )


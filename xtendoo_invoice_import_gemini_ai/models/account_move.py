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

    # Tracking: valores que extrajo Gemini originalmente
    gemini_extracted_partner = fields.Char(string="Proveedor extraído por Gemini", copy=False)
    gemini_extracted_date = fields.Char(string="Fecha extraída por Gemini", copy=False)
    gemini_extracted_ref = fields.Char(string="Referencia extraída por Gemini", copy=False)
    gemini_extracted_lines_count = fields.Integer(
        string="Nº líneas extraídas por Gemini", default=0, copy=False,
    )

    # Flag: se activa cuando Gemini procesa el asiento.
    # El usuario lo desactiva pulsando "Enseñar a Gemini" para confirmar que los datos son correctos.
    gemini_has_corrections = fields.Boolean(
        string="Pendiente de enseñar a Gemini",
        default=False,
        copy=False,
    )


    def action_teach_gemini(self):
        """
        Guarda el asiento correcto como ejemplo JSON para que en futuras
        extracciones similares Gemini lo use como referencia directa.
        """
        self.ensure_one()

        # Construir el JSON correcto del asiento tal como debe quedar
        journal_lines_example = []
        for line in self.line_ids:
            journal_lines_example.append({
                "account_code": line.account_id.code,
                "account_name": line.account_id.name,
                "description": line.name,
                "debit": line.debit,
                "credit": line.credit,
            })

        example_json = json.dumps({
            "journal_lines": journal_lines_example,
            "totals": {"total": sum(l["debit"] for l in journal_lines_example)},
        }, ensure_ascii=False, indent=2)

        learned_note = (
            f"Para documentos similares a este (ref: {self.ref or 'sin ref'}), "
            f"usa EXACTAMENTE este asiento:\n{example_json}"
        )

        self.env["gemini.feedback"].create({
            "source_model": "account.move",
            "move_id": self.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "gemini_partner_name": self.gemini_extracted_partner,
            "gemini_date": self.gemini_extracted_date,
            "gemini_description": self.gemini_extracted_ref,
            "correct_partner_name": self.partner_id.name if self.partner_id else False,
            "correct_date": str(self.invoice_date) if self.invoice_date else False,
            "correct_description": self.ref,
            "notes": learned_note,
        })
        self.gemini_has_corrections = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gemini aprendió"),
                "message": _("El asiento correcto ha sido guardado como ejemplo para futuras extracciones."),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def create(self, vals):
        print("*"*50)
        print("Entra al create")
        """Override create to trigger auto scan after creation if attachment is present."""
        move = super(AccountMove, self).create(vals)
        if move.state == 'draft':
            print("Move created in draft state, checking for auto scan...")
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

        # Don't process if already processed or if not a draft document
        if self.gemini_auto_processed or self.state != 'draft':
            return

        # Only process vendor bills
        if self.move_type != 'in_invoice':
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

    @api.model
    def create_document_from_attachment(self, name=None, attachment_ids=None):
        """
        Odoo uploader llama: create_document_from_attachment("", [ids])
        Crea un asiento contable (move_type='entry') y lo escanea con Gemini AI.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided."))

        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_("No general journal found for company %s.") % self.env.company.name)

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        created_moves = self.env['account.move']

        auto_scan_mode = (
            self.env["ir.config_parameter"].sudo()
            .get_param("xtendoo_invoice_import_gemini_ai.gemini_auto_scan", "disabled")
        )
        summary_mode = (auto_scan_mode == 'summary')

        for attachment in attachments:
            move = self.create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'state': 'draft',
                'date': fields.Date.context_today(self),
            })
            attachment.write({'res_model': 'account.move', 'res_id': move.id})
            created_moves |= move
            _logger.info(f"Created journal entry {move.id} from attachment {attachment.id}")
            try:
                move._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
            except Exception as e:
                _logger.warning(f"Gemini AI failed for move {move.id}: {e}")

        if created_moves:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journal Entry'),
                'res_model': 'account.move',
                'res_id': created_moves[0].id,
                'views': [[self.env.ref('account.view_move_form').id, 'form']],
                'target': 'current',
            }
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _process_with_gemini(self, summary_mode=False, auto_mode=False):
        self.ensure_one()
        if self.state != "draft":
            if not auto_mode:
                raise UserError(_("You can only import AI data on draft invoices."))
            return
        if self.move_type not in ('in_invoice', 'entry'):
            if not auto_mode:
                raise UserError(_("AI import is only available for vendor bills and journal entries."))
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
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if json_match:
                    raw_text = json_match.group(1)

            ai_data = json.loads(raw_text)
            _logger.warning(
                "GEMINI_DEBUG move=%s move_type=%s keys=%s journal_lines=%d lines=%d\nRAW:%s",
                self.id, self.move_type, list(ai_data.keys()),
                len(ai_data.get("journal_lines", [])),
                len(ai_data.get("lines", [])),
                raw_text[:1000],
            )

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
        """Prompt diferenciado: asientos entry usan journal_lines con debe/haber."""
        # Para entry el partner no existe aún al crear el asiento.
        # Buscamos todos los feedbacks de asientos sin filtrar por partner.
        if self.move_type == 'entry':
            feedback_context = self.env["gemini.feedback"].get_feedback_context_for_prompt(
                partner_id=None, source_model='account.move'
            )
        else:
            partner_id = self.partner_id.id if self.partner_id else None
            feedback_context = self.env["gemini.feedback"].get_feedback_context_for_prompt(
                partner_id=partner_id
            )

        if self.move_type == 'entry':
            prompt = (
                "Eres un asistente contable experto. Extrae los datos de este documento "
                "y devuelve un JSON con el asiento contable correcto.\n\n"
                "Estructura requerida:\n"
                "{\n"
                '    "supplier": {\n'
                '        "name": "Nombre del emisor del documento",\n'
                '        "vat": "NIF/CIF",\n'
                '        "address": "Dirección"\n'
                "    },\n"
                '    "invoice": {\n'
                '        "number": "Número de referencia del documento",\n'
                '        "date": "YYYY-MM-DD"\n'
                "    },\n"
                '    "journal_lines": [\n'
                "        {\n"
                '            "account_code": "100000",\n'
                '            "account_name": "Nombre de la cuenta contable",\n'
                '            "description": "Descripción del apunte",\n'
                '            "debit": 37.90,\n'
                '            "credit": 0.00\n'
                "        },\n"
                "        {\n"
                '            "account_code": "104000",\n'
                '            "account_name": "Nombre de la cuenta contable",\n'
                '            "description": "Descripción del apunte",\n'
                '            "debit": 0.00,\n'
                '            "credit": 37.90\n'
                "        }\n"
                "    ],\n"
                '    "totals": {\n'
                '        "total": 37.90\n'
                "    }\n"
                "}\n\n"
                "REGLAS OBLIGATORIAS:\n"
                "- suma(debit) debe ser igual a suma(credit) para que el asiento esté equilibrado\n"
                "- Usa códigos del Plan General Contable español (PGC)\n"
                "- Identifica el tipo de operación correctamente (aportación de capital, compra, venta, nómina, etc.)\n"
                "- Devuelve SOLO el JSON, sin ningún texto adicional."
            )
        else:
            prompt = (
                "Extract all data from this invoice and return it in JSON format.\n"
                "Required structure:\n"
                "{\n"
                '    "supplier": {"name": "...", "vat": "...", "address": "..."},\n'
                '    "invoice": {"number": "...", "date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD or null", "currency": "EUR"},\n'
                '    "lines": [{"description": "...", "quantity": 1.0, "unit_price": 100.00, "tax_percent": 21.0}],\n'
                '    "totals": {"untaxed": 100.00, "tax": 21.00, "total": 121.00}\n'
                "}\n"
            )

        if feedback_context:
            prompt += feedback_context

        if self.move_type != 'entry':
            if summary_mode:
                prompt += "\nIMPORTANT: In 'lines', group all items by VAT percentage. One line per VAT group."
            else:
                prompt += "\nIMPORTANT: Extract ALL individual line items from the invoice."
            prompt += "\nIdentify tax rates correctly (e.g., 21, 10, 4, 0). Return ONLY the JSON object."

        return prompt

    def _apply_gemini_data(self, data, summary_mode=False):
        """Aplica los datos extraídos. Para entry crea líneas de diario con debit/credit."""
        self.ensure_one()

        supplier_data = data.get("supplier", {})
        invoice_data = data.get("invoice", {})

        # 1. Partner
        partner = self._find_partner(supplier_data)
        if not partner and supplier_data.get("name"):
            partner = self.env["res.partner"].create({
                "name": supplier_data.get("name", "Unknown Supplier"),
                "vat": supplier_data.get("vat", False),
                "street": supplier_data.get("address", False),
                "supplier_rank": 1,
            })
        if partner:
            self.partner_id = partner

        # 2. Cabecera
        if invoice_data.get("number"):
            self.ref = invoice_data["number"]
        if invoice_data.get("date"):
            self.invoice_date = invoice_data["date"]
            self.date = invoice_data["date"]
        if invoice_data.get("due_date") and self.move_type != 'entry':
            self.invoice_date_due = invoice_data["due_date"]
        if invoice_data.get("currency") and self.move_type != 'entry':
            currency = self.env["res.currency"].search(
                [("name", "=", invoice_data["currency"].upper())], limit=1
            )
            if currency:
                self.currency_id = currency

        # 3. Líneas — comportamiento diferente según tipo
        if self.move_type == 'entry':
            # Asiento contable: crear líneas de diario con debe/haber
            journal_lines = data.get("journal_lines", [])
            if journal_lines:
                self.line_ids = [(5, 0, 0)]
                lines_to_create = []
                for jl in journal_lines:
                    code = str(jl.get("account_code", "")).strip()
                    account = self.env["account.account"].search(
                        [("code", "=", code), ("company_id", "=", self.company_id.id)],
                        limit=1,
                    )
                    if not account:
                        # Búsqueda parcial por prefijo
                        account = self.env["account.account"].search(
                            [("code", "=like", code + "%"), ("company_id", "=", self.company_id.id)],
                            limit=1,
                        )
                    if not account:
                        _logger.warning(f"Account not found for code: {code} in entry {self.id}")
                        continue
                    lines_to_create.append((0, 0, {
                        "account_id": account.id,
                        "name": jl.get("description") or invoice_data.get("number", "/"),
                        "debit": float(jl.get("debit", 0.0)),
                        "credit": float(jl.get("credit", 0.0)),
                        "partner_id": partner.id if partner else False,
                    }))
                if lines_to_create:
                    self.line_ids = lines_to_create
                    _logger.info(f"Created {len(lines_to_create)} journal lines for entry {self.id}")
                else:
                    _logger.warning(f"No journal lines created for entry {self.id} — accounts not found in PGC")
            else:
                _logger.warning(f"Gemini returned no journal_lines for entry {self.id}")
        else:
            # Factura de compra: crear líneas de factura
            lines_data = data.get("lines", [])
            self.invoice_line_ids = [(5, 0, 0)]
            default_account = self._get_default_expense_account()
            lines_to_create = []
            for line in lines_data:
                tax = self._find_tax(line.get("tax_percent"))
                lines_to_create.append((0, 0, {
                    "name": line.get("description", "Imported line"),
                    "quantity": line.get("quantity", 1.0),
                    "price_unit": line.get("unit_price", 0.0),
                    "account_id": default_account.id if default_account else False,
                    "tax_ids": [(6, 0, [tax.id])] if tax else [],
                }))
            self.invoice_line_ids = lines_to_create

        # 4. Guardar valores originales en un único write
        self.write({
            "gemini_extracted_partner": supplier_data.get("name", ""),
            "gemini_extracted_date": invoice_data.get("date", ""),
            "gemini_extracted_ref": invoice_data.get("number", ""),
            "gemini_extracted_lines_count": len(self.line_ids),
            "gemini_auto_processed": True,
            "gemini_has_corrections": True,
        })

    def _find_partner(self, supplier_data):
        vat = supplier_data.get("vat")
        name = supplier_data.get("name")

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


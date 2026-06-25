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
    # Se reactiva con cualquier modificación posterior del usuario.
    # El usuario lo desactiva pulsando "Enseñar a Gemini".
    gemini_has_corrections = fields.Boolean(
        string="Pendiente de enseñar a Gemini",
        default=False,
        copy=False,
    )


    def action_teach_gemini(self):
        """
        Guarda/fusiona el feedback del documento correcto para este emisor.
        - entry: guarda líneas de diario con debe/haber.
        - in_invoice: guarda líneas de factura con impuesto, cuenta, precio.
        Las líneas siempre reflejan la última corrección del usuario.
        """
        self.ensure_one()

        emisor_name = (
            self.partner_id.name if self.partner_id
            else self.gemini_extracted_partner or ""
        )

        if self.move_type == 'entry':
            lines_example = []
            for line in self.line_ids:
                lines_example.append({
                    "account_code": line.account_id.code if line.account_id else "",
                    "account_name": line.account_id.name if line.account_id else "",
                    "description": line.name or "",
                    "debit": line.debit,
                    "credit": line.credit,
                })
            notes = (
                f"Emisor: '{emisor_name}'. Asiento contable corregido por el usuario. "
                f"Usa las cuentas de correct_lines_json ajustando los importes al documento actual."
            )
        else:
            # Factura de compra: guardar tax_id (ID real de Odoo), tax_name y account_code
            lines_example = []
            for line in self.invoice_line_ids:
                tax_id_ref = line.tax_ids[0].id if line.tax_ids else None
                tax_name = line.tax_ids[0].name if line.tax_ids else None
                tax_percent = line.tax_ids[0].amount if line.tax_ids else None
                lines_example.append({
                    "description": line.name or "",
                    "quantity": line.quantity,
                    "unit_price": line.price_unit,
                    "tax_id": tax_id_ref,
                    "tax_name": tax_name,
                    "tax_percent": tax_percent,
                    "account_code": line.account_id.code if line.account_id else "",
                    "account_name": line.account_id.name if line.account_id else "",
                })
            notes = (
                f"Emisor: '{emisor_name}'. Factura de compra corregida. "
                f"Python aplica el impuesto directamente usando tax_id."
            )

        correct_lines_json = json.dumps(lines_example, ensure_ascii=False, indent=2)

        new_vals = {
            "source_model": "account.move",
            "move_id": self.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "gemini_partner_name": self.gemini_extracted_partner or "",
            "gemini_date": self.gemini_extracted_date or "",
            "gemini_description": self.gemini_extracted_ref or "",
            "correct_partner_name": emisor_name,
            "correct_date": str(self.invoice_date) if self.invoice_date else "",
            "correct_description": self.ref or "",
            "correct_lines_json": correct_lines_json,
            "notes": notes,
        }
        # Siempre crear un registro nuevo para conservar el historial.
        # find_all_for_emisor devuelve TODOS de mas antiguo a mas reciente;
        # el mas reciente prevalece al fusionar en _apply_feedback_taxes.
        self.env["gemini.feedback"].create(new_vals)
        all_fb = self.env["gemini.feedback"].find_all_for_emisor(
            partner_id=self.partner_id.id if self.partner_id else None,
            partner_name=emisor_name or None,
        )
        _logger.info(
            "Nuevo feedback creado para emisor '%s'. Total acumulados: %d",
            emisor_name, len(all_fb),
        )

        self.gemini_has_corrections = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gemini aprendió"),
                "message": _(
                    "Las correcciones han sido guardadas. "
                    "La próxima vez que se suba un documento de '%s', "
                    "Gemini usará estos datos automáticamente."
                ) % (emisor_name or _("este emisor")),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger auto scan after creation while supporting batch creates."""
        moves = super().create(vals_list)
        for move in moves.filtered(lambda record: record.state == "draft"):
            move._auto_scan_if_configured()
        return moves

    def write(self, vals):
        """Reactiva gemini_has_corrections cuando el usuario modifica el asiento
        después de que Gemini lo haya procesado, para que el botón aparezca."""
        gemini_internal_fields = {
            'gemini_has_corrections', 'gemini_auto_processed',
            'gemini_extracted_partner', 'gemini_extracted_date',
            'gemini_extracted_ref', 'gemini_extracted_lines_count',
            'gemini_attachment_id',
        }
        # Solo reactivar si:
        # 1. El usuario toca campos que no son internos de Gemini
        # 2. No se está escribiendo explícitamente gemini_has_corrections (ej: al enseñar)
        user_changed_fields = set(vals.keys()) - gemini_internal_fields
        if user_changed_fields and 'gemini_has_corrections' not in vals:
            for rec in self:
                if rec.gemini_auto_processed:
                    vals['gemini_has_corrections'] = True
                    break
        res = super().write(vals)
        # Trigger auto scan para facturas de compra
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
        """
        Para asientos (entry): los feedbacks van SIEMPRE al inicio del prompt,
        sin ninguna condición. Gemini lee el documento, identifica el emisor
        y aplica las cuentas aprendidas por sí mismo.
        """
        if self.move_type == 'entry':
            # SIEMPRE todos los feedbacks, al inicio, sin condiciones ni búsquedas previas.
            # Gemini identificará el emisor leyendo el documento y aplicará lo que corresponde.
            feedback_context = self.env["gemini.feedback"].get_all_feedback_context_for_prompt()
            if feedback_context:
                _logger.info("GEMINI_FEEDBACK: enviando %d chars de contexto al prompt", len(feedback_context))
            else:
                _logger.info("GEMINI_FEEDBACK: sin feedback previo, Gemini deducirá el asiento")

            # El feedback va AL INICIO — máxima prioridad para Gemini
            prompt = ""
            if feedback_context:
                prompt += feedback_context + "\n\n"

            prompt += (
                "Eres un asistente contable experto. Analiza el documento adjunto "
                "y devuelve ÚNICAMENTE un JSON con el asiento contable.\n\n"
                "PASOS:\n"
                "1. Identifica el nombre del emisor del documento.\n"
                "2. Busca ese emisor en las INSTRUCCIONES PREVIAS al inicio de este mensaje.\n"
                "3. Si el emisor aparece: usa EXACTAMENTE esas cuentas contables, "
                "ajustando los importes debit/credit al total real del documento "
                "pero manteniendo las mismas cuentas.\n"
                "4. Si el emisor NO aparece: deduce el asiento según el PGC español.\n\n"
                "Formato JSON requerido:\n"
                "{\n"
                '  "supplier": {"name": "Nombre emisor", "vat": "NIF/CIF", "address": "Dirección"},\n'
                '  "invoice": {"number": "Referencia", "date": "YYYY-MM-DD"},\n'
                '  "journal_lines": [\n'
                '    {"account_code": "400000", "account_name": "Proveedores", "description": "...", "debit": 0.00, "credit": 121.00},\n'
                '    {"account_code": "600000", "account_name": "Compras", "description": "...", "debit": 100.00, "credit": 0.00},\n'
                '    {"account_code": "472000", "account_name": "H.P. IVA soportado", "description": "...", "debit": 21.00, "credit": 0.00}\n'
                "  ],\n"
                '  "totals": {"total": 121.00}\n'
                "}\n\n"
                "REGLAS:\n"
                "- suma(debit) DEBE ser igual a suma(credit).\n"
                "- Usa códigos del Plan General Contable español (PGC).\n"
                "- Devuelve SOLO el JSON, sin texto adicional, sin markdown."
            )
            return prompt
        else:
            # Para facturas también usamos TODOS los feedbacks al inicio.
            # El partner no existe aún al subir el PDF, Gemini identifica el proveedor
            # y aplica tax_percent y account_code del feedback correspondiente.
            feedback_context = self.env["gemini.feedback"].get_all_feedback_context_for_prompt()
            if feedback_context:
                _logger.info("GEMINI_FEEDBACK (invoice): enviando %d chars al prompt", len(feedback_context))
            else:
                _logger.info("GEMINI_FEEDBACK (invoice): sin feedback previo")

            prompt = ""
            if feedback_context:
                prompt += feedback_context + "\n\n"
            prompt += (
                "Extract all data from this invoice and return it in JSON format.\n\n"
                "STEPS:\n"
                "1. Identify the supplier name from the document.\n"
                "2. Check if that supplier appears in the PREVIOUS INSTRUCTIONS above.\n"
                "3. If found: use EXACTLY those account_code values for each line. "
                "Adjust descriptions, quantities and unit prices from the document "
                "but do NOT change account_code. "
                "NOTE: taxes are managed by the system automatically.\n"
                "4. If not found: extract data normally.\n\n"
                "Required JSON structure:\n"
                "{\n"
                '    "supplier": {"name": "...", "vat": "...", "address": "..."},\n'
                '    "invoice": {"number": "...", "date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD or null", "currency": "EUR"},\n'
                '    "lines": [{"description": "...", "quantity": 1.0, "unit_price": 100.00, "tax_percent": 21.0, "account_code": "600000"}],\n'
                '    "totals": {"untaxed": 100.00, "tax": 21.00, "total": 121.00}\n'
                "}\n"
            )
            if summary_mode:
                prompt += "\nIMPORTANT: In 'lines', group all items by VAT percentage. One line per VAT group."
            else:
                prompt += "\nIMPORTANT: Extract ALL individual line items from the invoice."
            prompt += "\nReturn ONLY the JSON object, no markdown, no extra text."
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
                        [("code", "=", code), ("company_ids", "=", self.company_id.id)],
                        limit=1,
                    )
                    if not account:
                        # Búsqueda parcial por prefijo
                        account = self.env["account.account"].search(
                            [("code", "=like", code + "%"), ("company_ids", "=", self.company_id.id)],
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
                # Usar account_code del feedback si Gemini lo devuelve
                account = None
                code = str(line.get("account_code", "")).strip()
                if code:
                    account = self.env["account.account"].search(
                        [("code", "=", code), ("company_ids", "=", self.company_id.id)], limit=1
                    )
                    if not account:
                        account = self.env["account.account"].search(
                            [("code", "=like", code + "%"), ("company_ids", "=", self.company_id.id)], limit=1
                        )
                if not account:
                    account = default_account
                lines_to_create.append((0, 0, {
                    "name": line.get("description", "Imported line"),
                    "quantity": line.get("quantity", 1.0),
                    "price_unit": line.get("unit_price", 0.0),
                    "account_id": account.id if account else False,
                    "tax_ids": [(6, 0, [tax.id])] if tax else [],
                }))
            self.invoice_line_ids = lines_to_create
            # Sobreescribir impuestos con los del feedback (evita el impuesto incorrecto de Gemini)
            self._apply_feedback_taxes_to_invoice_lines()

        # 4. Guardar valores originales en un único write
        self.write({
            "gemini_extracted_partner": supplier_data.get("name", ""),
            "gemini_extracted_date": invoice_data.get("date", ""),
            "gemini_extracted_ref": invoice_data.get("number", ""),
            "gemini_extracted_lines_count": len(self.line_ids),
            "gemini_auto_processed": True,
            "gemini_has_corrections": True,
        })

    def _apply_feedback_taxes_to_invoice_lines(self):
        """
        Para facturas de compra: fusiona TODOS los feedbacks del proveedor de mas antiguo
        a mas reciente. Construye un mapa de impuesto POR LINEA usando la descripcion
        como clave de matching. El feedback mas reciente prevalece linea a linea.
        Para lineas sin match exacto se usa el impuesto por defecto (el mas reciente global).
        """
        if self.move_type != "in_invoice" or not self.partner_id:
            return

        all_feedbacks = self.env["gemini.feedback"].find_all_for_emisor(
            partner_id=self.partner_id.id,
            partner_name=self.partner_id.name,
        )
        if not all_feedbacks:
            return

        _logger.info(
            "_apply_feedback_taxes: fusionando %d feedbacks para partner_id=%s",
            len(all_feedbacks), self.partner_id.id,
        )

        # Construir mapa description_lower -> {tax_id, tax_name}
        # De mas antiguo a mas reciente: el mas reciente sobreescribe para cada descripcion.
        # default_tax_info: el ultimo tax visto (fallback para lineas sin match exacto).
        line_tax_map = {}
        default_tax_info = None

        for fb in all_feedbacks:
            if not fb.correct_lines_json:
                continue
            try:
                flines = json.loads(fb.correct_lines_json)
            except Exception:
                _logger.warning("Error parseando correct_lines_json del feedback %s", fb.id)
                continue
            for fl in flines:
                if not fl.get("tax_id"):
                    continue
                tax_info = {
                    "tax_id": int(fl["tax_id"]),
                    "tax_name": fl.get("tax_name", ""),
                }
                desc = (fl.get("description") or "").strip().lower()
                if desc:
                    line_tax_map[desc] = tax_info
                # El ultimo siempre actualiza el default (mas reciente gana)
                default_tax_info = tax_info

        if not line_tax_map and not default_tax_info:
            _logger.warning("_apply_feedback_taxes: ningun feedback tiene tax_id")
            return

        # Cache de impuestos resueltos para evitar busquedas repetidas
        tax_cache = {}

        def resolve_tax(tax_id, tax_name):
            key = (tax_id, tax_name)
            if key in tax_cache:
                return tax_cache[key]
            tax = None
            if tax_id:
                tax = self.env["account.tax"].browse(tax_id).exists()
                if not tax:
                    tax = None
            if not tax and tax_name:
                tax = self.env["account.tax"].search([
                    ("name", "=", tax_name),
                    ("type_tax_use", "=", "purchase"),
                ], limit=1)
            tax_cache[key] = tax
            return tax

        applied = 0
        for line in self.invoice_line_ids:
            desc_key = (line.name or "").strip().lower()

            # 1. Coincidencia exacta por descripcion
            tax_info = line_tax_map.get(desc_key)

            # 2. Coincidencia parcial (feedback contiene la desc de la linea o viceversa)
            if not tax_info and desc_key:
                for fb_desc, ti in line_tax_map.items():
                    if fb_desc and (fb_desc in desc_key or desc_key in fb_desc):
                        tax_info = ti
                        break

            # 3. Fallback: impuesto mas reciente global
            if not tax_info:
                tax_info = default_tax_info

            if not tax_info:
                continue

            tax = resolve_tax(tax_info["tax_id"], tax_info["tax_name"])
            if tax:
                line.tax_ids = [(6, 0, [tax.id])]
                applied += 1
                _logger.info(
                    "  Linea '%s' -> impuesto '%s' (id=%s)",
                    line.name, tax.name, tax.id,
                )
            else:
                _logger.warning(
                    "  Linea '%s': impuesto no encontrado (tax_id=%s, tax_name=%s)",
                    line.name, tax_info["tax_id"], tax_info["tax_name"],
                )

        _logger.info(
            "_apply_feedback_taxes: aplicado a %d/%d lineas de factura %s",
            applied, len(self.invoice_line_ids), self.id,
        )

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
                ("company_ids", "=", self.company_id.id),
            ],
            limit=1,
        )

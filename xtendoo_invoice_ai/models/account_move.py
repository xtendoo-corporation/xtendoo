# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import json
import logging
import os
import re
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openai
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_invoice_file = fields.Binary(
        string="AI Invoice File",
        help="Upload invoice file to analyze with AI",
        copy=False,
    )
    ai_invoice_filename = fields.Char(
        string="AI Filename",
        copy=False
    )
    ai_extracted_data = fields.Text(
        string="AI Extracted Data (Original)",
        help="Original JSON data extracted by AI for comparison and feedback",
        copy=False,
    )
    ai_feedback_sent = fields.Boolean(
        string="Feedback Sent to AI",
        default=False,
        copy=False,
        help="Indicates if corrections feedback has been sent to improve AI",
    )
    ai_import_date = fields.Datetime(
        string="AI Import Date",
        copy=False,
        help="When the AI import was performed",
    )

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """
        ✅ NUEVO: Procesar emails entrantes con facturas adjuntas.
        Este método se llama cuando llega un email al alias configurado en el journal.
        """
        _logger.info(f"📧 Received email for invoice creation: {msg_dict.get('subject', 'No subject')}")

        # Obtener el journal desde custom_values o alias_defaults
        journal_id = None
        if custom_values and custom_values.get("journal_id"):
            journal_id = custom_values.get("journal_id")

        if not journal_id:
            _logger.error("❌ No journal_id found in custom_values, cannot process invoice email")
            return super().message_new(msg_dict, custom_values=custom_values)

        journal = self.env["account.journal"].browse(journal_id)

        # Verificar que el journal tiene habilitada la importación por IA
        if not journal.ai_invoice_alias_enabled:
            _logger.info(f"ℹ️ AI invoice import not enabled for journal {journal.name}")
            return super().message_new(msg_dict, custom_values=custom_values)

        # Procesar adjuntos de facturas
        attachments = msg_dict.get("attachments", [])
        if not attachments:
            _logger.info("ℹ️ No attachments found in email")
            return super().message_new(msg_dict, custom_values=custom_values)

        _logger.info(f"📎 Processing {len(attachments)} attachments from email")

        created_invoices = []

        for attachment in attachments:
            try:
                filename = attachment[0]
                file_content = attachment[1]

                # ✅ IMPORTANTE: Los adjuntos en msg_dict NO vienen en base64,
                # pero el wizard espera base64. Necesitamos codificar.
                if isinstance(file_content, bytes):
                    file_content = base64.b64encode(file_content)
                elif isinstance(file_content, str):
                    # Si es string, asumir que es base64 ya
                    file_content = file_content.encode() if isinstance(file_content, str) else file_content

                # Validar tipo de archivo
                if not self._is_valid_invoice_file(filename):
                    _logger.info(f"⏭️ Skipping non-invoice file: {filename}")
                    continue

                _logger.info(f"🔄 Processing invoice file: {filename}")

                # Crear factura(s) usando el wizard de IA
                result = self._create_invoice_from_attachment(
                    filename, file_content, msg_dict, journal
                )

                # result puede ser una factura o una lista de facturas (multi-page)
                if result:
                    if isinstance(result, list):
                        created_invoices.extend(result)
                    else:
                        created_invoices.append(result)

            except Exception as e:
                _logger.error(f"❌ Error processing attachment {filename}: {str(e)}", exc_info=True)

        # Enviar notificación al remitente
        if created_invoices:
            self._send_processing_notification(
                msg_dict.get("email_from"),
                len(created_invoices),
                len(attachments) - len(created_invoices),
                msg_dict.get("message_id"),
                journal,
            )

        # Retornar la primera factura creada (o crear una vacía si no se procesó nada)
        if created_invoices:
            _logger.info(f"✅ Successfully created {len(created_invoices)} invoice(s) from email")
            return created_invoices[0]
        else:
            _logger.warning("⚠️ No invoices were created from email attachments")
            return super().message_new(msg_dict, custom_values=custom_values)

    def _is_valid_invoice_file(self, filename):
        """✅ NUEVO: Verificar si el archivo es un tipo válido para facturas"""
        if not filename:
            return False

        filename_lower = filename.lower()
        valid_extensions = (".pdf", ".jpg", ".jpeg", ".png")
        return filename_lower.endswith(valid_extensions)

    def _create_invoice_from_attachment(self, filename, file_content, msg_dict, journal):
        """
        ✅ NUEVO: Crear factura(s) borrador usando el wizard de IA.
        ✨ MULTI-INVOICE: Detecta automáticamente PDFs con múltiples páginas y crea una factura por página.
        """
        # Detectar si el PDF tiene múltiples páginas
        multi_invoice = False
        if filename.lower().endswith('.pdf'):
            try:
                # Decodificar el PDF para contar páginas
                pdf_data = base64.b64decode(file_content)
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(pdf_data, first_page=1, last_page=2)  # Solo verificar primeras 2 páginas
                if len(images) > 1:
                    multi_invoice = True
                    _logger.info(f"📄 PDF has multiple pages, enabling multi-invoice mode")
            except Exception as e:
                _logger.warning(f"Could not detect page count, assuming single page: {e}")

        # Crear wizard
        wizard = self.env["xtendoo.invoice.ai.wizard"].create({
            "upload": file_content,
            "filename": filename,
            "company_id": journal.company_id.id,
            "journal_id": journal.id,
            "create_partner_if_missing": journal.ai_invoice_create_partner,
            "attach_original": journal.ai_invoice_attach_original,
            "multi_invoice": multi_invoice,  # ✅ Activar modo multi-factura si hay múltiples páginas
        })

        # Procesar con IA
        result = wizard.action_analyze_and_create()

        # Preparar nota de email
        email_from = msg_dict.get("email_from", "Unknown")
        subject = msg_dict.get("subject", "No subject")

        note = _(
            "📧 Invoice received by email\n"
            "From: %s\n"
            "Subject: %s\n"
            "Processed automatically with AI"
        ) % (email_from, subject)

        # Manejar resultado según sea single o multi-invoice
        if multi_invoice:
            # Multi-invoice: result contiene domain con IDs de facturas
            if result.get("domain"):
                invoice_ids = result["domain"][0][2]  # [('id', 'in', [1,2,3])]
                invoices = self.env["account.move"].browse(invoice_ids)

                # Añadir nota a todas las facturas
                for invoice in invoices:
                    current_narration = invoice.narration or ""
                    invoice.narration = current_narration + "\n\n" + note if current_narration else note

                _logger.info(f"✅ Created {len(invoices)} invoices from multi-page email attachment {filename}")

                # Retornar lista de facturas
                return list(invoices) if invoices else None
        else:
            # Single invoice: result contiene res_id
            if result.get("res_id"):
                invoice = self.env["account.move"].browse(result["res_id"])

                # Añadir nota con información del email
                current_narration = invoice.narration or ""
                invoice.narration = current_narration + "\n\n" + note if current_narration else note

                _logger.info(f"✅ Created invoice {invoice.name} from email attachment {filename}")
                return invoice

        return None

    def _send_processing_notification(self, email_to, success_count, error_count, in_reply_to, journal):
        """
        ✅ NUEVO: Enviar notificación por email sobre el resultado del procesamiento.
        """
        if not email_to:
            return

        subject = _("Invoice Processing Result - %s") % journal.name

        if error_count == 0:
            body = _(
                "<p>Your invoice(s) have been successfully processed:</p>"
                "<ul>"
                "<li>✅ Successfully processed: <strong>%s</strong> invoice(s)</li>"
                "</ul>"
                "<p>The draft invoice(s) are now available in the system for review.</p>"
            ) % success_count
        else:
            body = _(
                "<p>Invoice processing completed with some issues:</p>"
                "<ul>"
                "<li>✅ Successfully processed: <strong>%s</strong> invoice(s)</li>"
                "<li>❌ Failed: <strong>%s</strong> invoice(s)</li>"
                "</ul>"
                "<p>Please check the system logs or contact support for failed invoices.</p>"
            ) % (success_count, error_count)

        # Crear y enviar email
        mail_values = {
            "subject": subject,
            "body_html": body,
            "email_to": email_to,
            "auto_delete": True,
        }

        if in_reply_to and journal.ai_invoice_alias_id:
            mail_values["reply_to"] = journal.ai_invoice_alias_id.display_name
            mail_values["headers"] = {"In-Reply-To": in_reply_to}

        try:
            mail = self.env["mail.mail"].create(mail_values)
            mail.send()
            _logger.info(f"📧 Sent processing notification to {email_to}")
        except Exception as e:
            _logger.error(f"❌ Failed to send notification email: {str(e)}")

    # ========== MÉTODOS ORIGINALES (sin cambios) ==========

    def action_import_invoice_with_ai(self):
        """Importar factura usando IA desde el botón en la factura"""
        self.ensure_one()

        # Buscar archivo en el campo binario o en adjuntos
        file_data = None
        filename = None

        if self.ai_invoice_file:
            file_data = self.ai_invoice_file
            filename = self.ai_invoice_filename
        else:
            # Buscar en adjuntos de la factura
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "account.move"),
                ("res_id", "=", self.id),
                ("mimetype", "in", ["application/pdf", "image/jpeg", "image/png", "image/jpg"]),
            ], limit=1, order="create_date desc")

            if attachments:
                file_data = attachments[0].datas
                filename = attachments[0].name
                _logger.info(f"Using attachment: {filename} for AI processing")

        if not file_data:
            raise UserError(
                _("Please upload an invoice file first. You can either use the 'AI Invoice File' field in the 'Importación IA' tab or attach a PDF/image file to this invoice."))

        if self.state != "draft":
            raise UserError(_("You can only import AI data on draft invoices."))

        if self.move_type != "in_invoice":
            raise UserError(_("AI import is only available for vendor bills."))

        # Usar el wizard para procesar
        wizard = self.env["xtendoo.invoice.ai.wizard"].create({
            "upload": file_data,
            "filename": filename,
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
            "currency_id": self.currency_id.id if self.currency_id else False,
            "create_partner_if_missing": True,
            "attach_original": True,
        })

        # Crear job
        job = self.env["xtendoo.invoice.ai.job"].create({
            "filename": self.ai_invoice_filename or filename,
            "state": "processing",
            "company_id": self.company_id.id,
            "user_id": self.env.user.id,
        })

        try:
            # Obtener credenciales
            credentials = wizard._get_openai_credentials()

            # Preparar imágenes
            images_b64 = wizard._prepare_images_for_openai()

            # Llamar a OpenAI
            openai_result = wizard._call_openai_vision(images_b64, credentials)

            # Validar schema
            wizard._validate_json_schema(openai_result["json_data"])

            # Actualizar la factura actual con los datos extraídos
            self._update_invoice_from_ai_data(openai_result["json_data"])

            # Adjuntar archivo original si no existe ya
            if file_data and not self.env["ir.attachment"].search([
                ("res_model", "=", "account.move"),
                ("res_id", "=", self.id),
                ("name", "=", filename or "invoice.pdf"),
            ], limit=1):
                self.env["ir.attachment"].create({
                    "name": filename or "invoice.pdf",
                    "datas": file_data,
                    "res_model": "account.move",
                    "res_id": self.id,
                    "type": "binary",
                })

            # Actualizar job
            meta = openai_result["json_data"].get("meta", {})
            job.write({
                "state": "done",
                "invoice_id": self.id,
                "tokens_used": openai_result["tokens_used"],
                "processing_time": openai_result["processing_time"],
                "pages_processed": meta.get("pages_processed", len(images_b64)),
                "detected_language": meta.get("language"),
                "detected_country": meta.get("detected_country"),
                "supplier_name": openai_result["json_data"]["supplier"]["name"],
                "invoice_number": openai_result["json_data"]["invoice"]["supplier_invoice_number"],
                "invoice_amount": openai_result["json_data"]["totals"]["total"],
            })

            # Limpiar campos temporales
            self.write({
                "ai_invoice_file": False,
                "ai_invoice_filename": False,
            })

            # Retornar acción para recargar la vista actual con notificación
            return {
                "type": "ir.actions.client",
                "tag": "reload",
                "params": {
                    "notification": {
                        "type": "success",
                        "title": _("Success"),
                        "message": _("Invoice data has been successfully imported from AI. The page will reload to show the changes."),
                        "sticky": False,
                    }
                }
            }

        except Exception as e:
            # Actualizar job con error
            job.write({
                "state": "error",
                "error_message": str(e),
            })
            raise

    def action_quick_import_invoice_ai(self):
        """Abrir wizard de importación rápida desde la vista de lista"""
        return {
            "name": _("Import Invoice with AI"),
            "type": "ir.actions.act_window",
            "res_model": "xtendoo.invoice.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_id": self.env.company.id,
                "default_create_partner_if_missing": True,
                "default_attach_original": True,
            },
        }

    def _update_invoice_from_ai_data(self, ai_data):
        """Actualizar factura existente con datos de IA"""
        supplier_data = ai_data["supplier"]
        invoice_data = ai_data["invoice"]
        lines_data = ai_data["lines"]
        totals_data = ai_data["totals"]

        # Obtener wizard para usar sus métodos auxiliares
        wizard = self.env["xtendoo.invoice.ai.wizard"].new({
            "company_id": self.company_id.id,
            "create_partner_if_missing": True,
        })

        # 1. Actualizar partner
        partner = wizard._find_or_create_partner(supplier_data)

        # 2. Actualizar datos de cabecera
        invoice_date = fields.Date.from_string(invoice_data["invoice_date"])
        due_date = None
        if invoice_data.get("due_date"):
            try:
                due_date = fields.Date.from_string(invoice_data["due_date"])
            except:
                pass

        vals = {
            "partner_id": partner.id,
            "invoice_date": invoice_date,
            "ref": invoice_data["supplier_invoice_number"],
        }

        if due_date:
            vals["invoice_date_due"] = due_date

        if invoice_data.get("notes"):
            vals["narration"] = invoice_data["notes"]

        self.with_context(check_move_validity=False).write(vals)
        # Forzar recálculo de campos relacionados con el partner
        if partner:
            self._onchange_partner_id()
            # Asegurar que los valores se mantienen después del onchange
            if invoice_date:
                self.invoice_date = invoice_date
            if invoice_data["supplier_invoice_number"]:
                self.ref = invoice_data["supplier_invoice_number"]
            if due_date:
                self.invoice_date_due = due_date

        # 3. Eliminar líneas existentes (excepto las de impuestos)
        self.invoice_line_ids.filtered(lambda l: not l.display_type).unlink()

        # 4. Crear nuevas líneas
        default_account = wizard._get_default_purchase_account()
        lines_to_create = []

        for line_data in lines_data:
            product = None
            account = default_account

            # Buscar producto por código
            if line_data.get("product_code"):
                product = self.env["product.product"].search(
                    [("default_code", "=", line_data["product_code"])],
                    limit=1,
                )

            # Si hay producto, usar su cuenta
            if product:
                account = (
                        product.property_account_expense_id
                        or product.categ_id.property_account_expense_categ_id
                        or default_account
                )

            # Mapear impuestos
            taxes = self.env["account.tax"]
            for tax_name in line_data.get("taxes", []):
                tax = wizard._map_tax_by_name(tax_name)
                if tax:
                    taxes |= tax
                    _logger.info(f"Tax '{tax_name}' mapped to: {tax.name} (ID: {tax.id}, Amount: {tax.amount}%)")
                else:
                    _logger.warning(f"Tax '{tax_name}' not found, skipping")

            # Si no se encontró ningún impuesto, usar el impuesto de compra por defecto
            if not taxes and partner.property_account_position_id:
                taxes = partner.property_account_position_id.map_tax(
                    taxes, product=product, partner=partner
                )

            _logger.info(f"Creating line: {line_data['description']}, qty: {line_data['quantity']}, "
                         f"price: {line_data['unit_price']}, taxes: {taxes.mapped('name')}")

            line_vals = {
                "move_id": self.id,
                "name": line_data["description"],
                "quantity": line_data["quantity"],
                "price_unit": line_data["unit_price"],
                "account_id": account.id,
                "tax_ids": [(6, 0, taxes.ids)],
            }

            if product:
                line_vals["product_id"] = product.id

            lines_to_create.append((0, 0, line_vals))

        # Crear todas las líneas de una vez
        self.write({"invoice_line_ids": lines_to_create})

        # 5. Validar totales
        _logger.info(f"Invoice totals after recompute - Untaxed: {self.amount_untaxed}, "
                     f"Tax: {self.amount_tax}, Total: {self.amount_total}")

        tolerance = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_ai.tolerance", default=0.02)
        )

        diff_untaxed = abs(self.amount_untaxed - totals_data["untaxed"])
        diff_total = abs(self.amount_total - totals_data["total"])

        if diff_untaxed > tolerance or diff_total > tolerance:
            _logger.warning(
                f"Total mismatch detected! AI: Untaxed={totals_data['untaxed']}, Total={totals_data['total']} | "
                f"Calculated: Untaxed={self.amount_untaxed}, Total={self.amount_total}"
            )
            # Añadir una nota en la factura
            current_narration = self.narration or ""
            warning_note = _(
                "\n\n⚠️ WARNING: Total mismatch detected!\n"
                "AI extracted: Untaxed=%.2f, Total=%.2f\n"
                "Calculated: Untaxed=%.2f, Total=%.2f\n"
                "Please review the invoice manually."
            ) % (
                               totals_data["untaxed"],
                               totals_data["total"],
                               self.amount_untaxed,
                               self.amount_total,
                           )
            self.narration = current_narration + warning_note

    def action_import_with_ai(self):
        """
        Importar factura con IA desde los adjuntos existentes.
        Busca el último adjunto PDF/imagen y lo procesa con IA.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Can only import AI data to draft invoices."))

        # Buscar adjuntos válidos (PDF, JPG, PNG) en esta factura
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']),
        ], order='create_date desc', limit=1)

        if not attachments:
            raise UserError(_("No invoice file found. Please attach a PDF or image (JPG/PNG) first using the attachments button (📎)."))

        attachment = attachments[0]
        _logger.info(f"🚀 Starting AI import for invoice {self.name} using attachment: {attachment.name}")

        try:
            # Obtener datos del archivo
            file_data = base64.b64decode(attachment.datas)
            filename = attachment.name

            # Procesar con IA
            result = self._process_invoice_with_ai(file_data, filename)

            if not result:
                raise UserError(_("Failed to extract data from invoice. Please check the OpenAI configuration."))

            # Mensaje de éxito en el chatter
            self.message_post(
                body=_("✅ Invoice data successfully imported from AI!<br/>File: %s") % filename,
                subject=_("AI Import Completed")
            )

            _logger.info(f"✅ AI import completed successfully for invoice {self.name}")

            # Retornar acción para recargar la vista
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Invoice data imported successfully!'),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"❌ Error importing invoice with AI: {error_msg}", exc_info=True)

            # Mensaje de error en el chatter
            self.message_post(
                body=_("❌ Error importing invoice: %s") % error_msg,
                subject=_("AI Import Failed")
            )

            raise UserError(_("Failed to import invoice: %s") % error_msg)

    def _process_invoice_with_ai(self, file_data, filename):
        """
        Procesar archivo de factura con IA y aplicar datos a esta factura.
        """
        self.ensure_one()

        # Obtener credenciales de OpenAI
        icp = self.env["ir.config_parameter"].sudo()
        api_key = icp.get_param("xtendoo_invoice_ai.openai_api_key") or os.environ.get("OPENAI_API_KEY")

        if not api_key:
            raise UserError(_("OpenAI API Key not configured. Please go to Settings → General → OpenAI and configure it."))

        model = icp.get_param("xtendoo_invoice_ai.openai_model", default="gpt-4o")
        max_pages = int(icp.get_param("xtendoo_invoice_ai.max_pages", default=10))
        temperature = float(icp.get_param("xtendoo_invoice_ai.temperature", default=0.0))

        # Convertir archivo a imágenes
        images_b64 = self._convert_file_to_images(file_data, filename, max_pages)

        if not images_b64:
            raise UserError(_("Failed to process the file. Make sure it's a valid PDF or image."))

        # Llamar a OpenAI
        invoice_data = self._call_openai_for_extraction(images_b64, api_key, model, temperature)

        if not invoice_data:
            raise UserError(_("Failed to extract data from invoice."))

        # Aplicar datos a la factura
        self._apply_extracted_data(invoice_data)

        return True

    def _convert_file_to_images(self, file_data, filename, max_pages=10):
        """Convertir archivo a lista de imágenes en base64."""
        filename_lower = filename.lower()

        if filename_lower.endswith('.pdf'):
            if not convert_from_bytes:
                raise UserError(_("pdf2image library not installed."))
            try:
                images = convert_from_bytes(file_data, fmt="jpeg", dpi=150)
                images_b64 = []
                for img in images[:max_pages]:
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG")
                    img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    images_b64.append(img_b64)
                return images_b64
            except Exception as e:
                _logger.error(f"Error converting PDF: {e}")
                raise UserError(_("Failed to convert PDF: %s") % str(e))
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png')):
            return [base64.b64encode(file_data).decode("utf-8")]
        else:
            raise UserError(_("Unsupported file format. Use PDF, JPG or PNG."))

    def _call_openai_for_extraction(self, images_b64, api_key, model, temperature):
        """Llamar a OpenAI para extraer datos de la factura."""
        if not OpenAI:
            raise UserError(_("openai library not installed."))

        client = OpenAI(api_key=api_key)

        # Obtener ejemplos de correcciones previas (few-shot learning)
        few_shot_examples = self._get_few_shot_examples(max_examples=3)

        # Prompt de extracción con few-shot learning
        extraction_prompt = f"""Extract ALL data from this invoice image and return ONLY valid JSON.

{few_shot_examples}

Required structure:
{{
    "supplier": {{
        "name": "Supplier company name",
        "vat": "Tax ID/VAT number",
        "address": "Full address",
        "email": "email@example.com",
        "phone": "phone number"
    }},
    "invoice": {{
        "supplier_invoice_number": "Invoice number from supplier",
        "invoice_date": "YYYY-MM-DD",
        "due_date": "YYYY-MM-DD or null",
        "currency": "EUR/USD/etc"
    }},
    "lines": [
        {{
            "description": "Product/service description",
            "quantity": 1.0,
            "unit_price": 100.00,
            "taxes": ["21% IVA", "10% IVA"]
        }}
    ],
    "totals": {{
        "untaxed": 100.00,
        "tax": 21.00,
        "total": 121.00
    }}
}}

IMPORTANT:
- Extract ALL line items
- Use correct decimal numbers
- Identify tax rates correctly (IVA 21%, IVA 10%, IVA 4%, etc.)
- Return ONLY the JSON, no markdown, no explanation
- Learn from the past corrections shown above"""

        # ...existing code...

        # Preparar contenido
        content = [{"type": "text", "text": extraction_prompt}]
        for img_b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}
            })

        # Detectar si es modelo o1
        is_o1 = model.lower().startswith("o1")

        if is_o1:
            messages = [{"role": "user", "content": content}]
        else:
            messages = [
                {"role": "system", "content": "You are a precise invoice data extraction assistant. Always return valid JSON."},
                {"role": "user", "content": content}
            ]

        try:
            api_params = {"model": model, "messages": messages}
            if not is_o1:
                api_params["temperature"] = temperature
                api_params["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**api_params)
            result_text = response.choices[0].message.content

            # Extraer JSON de bloques markdown si es necesario
            if "```json" in result_text:
                match = re.search(r'```json\s*\n(.*?)\n```', result_text, re.DOTALL)
                if match:
                    result_text = match.group(1)
            elif "```" in result_text:
                match = re.search(r'```\s*\n(.*?)\n```', result_text, re.DOTALL)
                if match:
                    result_text = match.group(1)

            return json.loads(result_text)

        except Exception as e:
            _logger.error(f"OpenAI API error: {e}")
            raise UserError(_("OpenAI API error: %s") % str(e))

    def _apply_extracted_data(self, data):
        """Aplicar datos extraídos por IA a esta factura."""
        self.ensure_one()

        # Guardar datos originales de IA para comparación y feedback
        self.write({
            'ai_extracted_data': json.dumps(data, indent=2),
            'ai_import_date': fields.Datetime.now(),
            'ai_feedback_sent': False,
        })

        supplier_data = data.get("supplier", {})
        invoice_data = data.get("invoice", {})
        lines_data = data.get("lines", [])
        totals_data = data.get("totals", {})

        # ...existing code...

        # 1. Buscar o crear partner
        partner = self._find_partner_by_vat(supplier_data.get("vat")) or \
                  self._find_partner_by_name(supplier_data.get("name"))

        if not partner and supplier_data.get("name"):
            # Crear partner
            partner = self.env["res.partner"].create({
                "name": supplier_data.get("name"),
                "vat": supplier_data.get("vat"),
                "street": supplier_data.get("address"),
                "email": supplier_data.get("email"),
                "phone": supplier_data.get("phone"),
                "supplier_rank": 1,
                "company_id": self.company_id.id,
            })
            _logger.info(f"Created new partner: {partner.name}")

        # 2. Actualizar cabecera
        vals = {}
        if partner:
            vals["partner_id"] = partner.id
        if invoice_data.get("supplier_invoice_number"):
            vals["ref"] = invoice_data["supplier_invoice_number"]
        if invoice_data.get("invoice_date"):
            try:
                vals["invoice_date"] = invoice_data["invoice_date"]
            except:
                pass
        if invoice_data.get("due_date"):
            try:
                vals["invoice_date_due"] = invoice_data["due_date"]
            except:
                pass

        if vals:
            self.write(vals)

        # 3. Eliminar líneas existentes
        self.invoice_line_ids.unlink()

        # 4. Crear nuevas líneas
        default_account = self._get_default_expense_account()

        for line_data in lines_data:
            # Mapear impuestos
            taxes = self.env["account.tax"]
            for tax_name in line_data.get("taxes", []):
                tax = self._find_tax_by_name(tax_name)
                if tax:
                    taxes |= tax

            line_vals = {
                "move_id": self.id,
                "name": line_data.get("description", ""),
                "quantity": line_data.get("quantity", 1),
                "price_unit": line_data.get("unit_price", 0),
                "account_id": default_account.id if default_account else False,
                "tax_ids": [(6, 0, taxes.ids)],
            }
            self.env["account.move.line"].create(line_vals)

        _logger.info(f"Applied {len(lines_data)} lines to invoice {self.name}")

    def _find_partner_by_vat(self, vat):
        """Buscar partner por VAT/NIF."""
        if not vat:
            return None
        vat_clean = vat.upper().replace(" ", "").replace("-", "").replace(".", "")
        return self.env["res.partner"].search([
            "|", ("vat", "=", vat), ("vat", "=", vat_clean)
        ], limit=1)

    def _find_partner_by_name(self, name):
        """Buscar partner por nombre."""
        if not name:
            return None
        return self.env["res.partner"].search([
            ("name", "ilike", name), ("supplier_rank", ">", 0)
        ], limit=1)

    def _get_default_expense_account(self):
        """Obtener cuenta de gastos por defecto."""
        # En Odoo 18, account.account ya no tiene company_id directo
        # Usamos el journal de compra para obtener la cuenta por defecto
        journal = self.journal_id or self.env["account.journal"].search([
            ("type", "=", "purchase"),
            ("company_id", "=", self.company_id.id),
        ], limit=1)

        if journal and journal.default_account_id:
            return journal.default_account_id

        # Alternativa: buscar cuenta de tipo expense sin filtro de compañía
        return self.env["account.account"].search([
            ("account_type", "=", "expense"),
        ], limit=1)

    def _find_tax_by_name(self, tax_name):
        """Buscar impuesto por nombre/porcentaje."""
        if not tax_name:
            return None

        # Extraer porcentaje del nombre
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', str(tax_name))
        if match:
            percentage = float(match.group(1).replace(",", "."))
            tax = self.env["account.tax"].search([
                ("company_id", "=", self.company_id.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", percentage),
            ], limit=1)
            if tax:
                return tax

        # Buscar por nombre
        return self.env["account.tax"].search([
            ("company_id", "=", self.company_id.id),
            ("type_tax_use", "=", "purchase"),
            ("name", "ilike", tax_name),
        ], limit=1)

    def action_send_ai_feedback(self):
        """
        Enviar feedback a la IA comparando lo que extrajo vs. lo que quedó finalmente.
        Esto crea un ejemplo de few-shot learning para mejorar futuras importaciones.
        """
        self.ensure_one()

        if not self.ai_extracted_data:
            raise UserError(_("No AI extracted data found. This invoice was not imported with AI."))

        if self.ai_feedback_sent:
            raise UserError(_("Feedback already sent for this invoice."))

        try:
            # Datos originales extraídos por IA
            ai_data = json.loads(self.ai_extracted_data)

            # Datos actuales (después de correcciones del usuario)
            current_data = self._extract_current_invoice_data()

            # Crear ejemplo de feedback
            feedback_example = self.env["xtendoo.ai.feedback.example"].create({
                "invoice_id": self.id,
                "supplier_name": self.partner_id.name if self.partner_id else "Unknown",
                "ai_extracted_json": json.dumps(ai_data, indent=2),
                "corrected_json": json.dumps(current_data, indent=2),
                "correction_type": self._determine_correction_type(ai_data, current_data),
                "quality_score": 7.0,  # Score inicial
                "notes": _("Auto-generated feedback from invoice %s") % self.name,
            })

            # Marcar como enviado
            self.ai_feedback_sent = True

            # Mensaje en el chatter
            self.message_post(
                body=_("✅ AI Feedback example created! This will help improve future imports.<br/>"
                       "Example ID: %s") % feedback_example.id,
                subject=_("AI Feedback Sent")
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Feedback Sent'),
                    'message': _('Thank you! This correction will help improve AI accuracy in future imports.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Error sending AI feedback: {e}", exc_info=True)
            raise UserError(_("Failed to send feedback: %s") % str(e))

    def _extract_current_invoice_data(self):
        """Extraer datos actuales de la factura en formato similar al JSON de IA."""
        self.ensure_one()

        return {
            "supplier": {
                "name": self.partner_id.name if self.partner_id else "",
                "vat": self.partner_id.vat if self.partner_id else "",
                "address": self.partner_id.street if self.partner_id else "",
                "email": self.partner_id.email if self.partner_id else "",
                "phone": self.partner_id.phone if self.partner_id else "",
            },
            "invoice": {
                "supplier_invoice_number": self.ref or "",
                "invoice_date": str(self.invoice_date) if self.invoice_date else "",
                "due_date": str(self.invoice_date_due) if self.invoice_date_due else "",
                "currency": self.currency_id.name if self.currency_id else "EUR",
            },
            "lines": [
                {
                    "description": line.name,
                    "quantity": line.quantity,
                    "unit_price": line.price_unit,
                    "taxes": [tax.name for tax in line.tax_ids],
                }
                for line in self.invoice_line_ids if not line.display_type
            ],
            "totals": {
                "untaxed": float(self.amount_untaxed),
                "tax": float(self.amount_tax),
                "total": float(self.amount_total),
            }
        }

    def _determine_correction_type(self, ai_data, corrected_data):
        """Determinar qué tipo de corrección se hizo."""
        # Comparar proveedores
        if ai_data.get("supplier", {}).get("name") != corrected_data.get("supplier", {}).get("name"):
            return "supplier"

        # Comparar número de líneas
        if len(ai_data.get("lines", [])) != len(corrected_data.get("lines", [])):
            return "lines"

        # Comparar totales
        ai_total = ai_data.get("totals", {}).get("total", 0)
        corrected_total = corrected_data.get("totals", {}).get("total", 0)
        if abs(ai_total - corrected_total) > 1.0:
            return "totals"

        # Comparar impuestos
        for ai_line, corr_line in zip(ai_data.get("lines", []), corrected_data.get("lines", [])):
            if set(ai_line.get("taxes", [])) != set(corr_line.get("taxes", [])):
                return "taxes"

        return "other"

    def _get_few_shot_examples(self, max_examples=3):
        """
        Obtener ejemplos de correcciones previas para incluir en el prompt (few-shot learning).
        Esto mejora la precisión de la IA mostrándole ejemplos de errores pasados.
        """
        # Buscar ejemplos de feedback activos, priorizando por quality_score
        examples = self.env["xtendoo.ai.feedback.example"].search([
            ("active", "=", True),
            ("company_id", "=", self.company_id.id),
        ], order="quality_score desc, create_date desc", limit=max_examples)

        if not examples:
            return ""

        few_shot_text = "\n\n--- LEARNING FROM PAST CORRECTIONS ---\n"
        few_shot_text += "Here are examples of past mistakes to avoid:\n\n"

        for idx, example in enumerate(examples, 1):
            try:
                ai_data = json.loads(example.ai_extracted_json)
                corrected_data = json.loads(example.corrected_json)

                few_shot_text += f"Example {idx} - What I extracted WRONG:\n"
                few_shot_text += f"Supplier: {ai_data.get('supplier', {}).get('name', 'N/A')}\n"
                few_shot_text += f"Total: {ai_data.get('totals', {}).get('total', 'N/A')}\n\n"

                few_shot_text += f"What it SHOULD have been:\n"
                few_shot_text += f"Supplier: {corrected_data.get('supplier', {}).get('name', 'N/A')}\n"
                few_shot_text += f"Total: {corrected_data.get('totals', {}).get('total', 'N/A')}\n"
                few_shot_text += f"Lesson: {example.correction_type}\n\n"
            except:
                continue

        few_shot_text += "Please learn from these corrections and be more accurate this time.\n"
        few_shot_text += "--- END OF CORRECTIONS ---\n\n"

        return few_shot_text


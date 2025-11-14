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
    # ✅ account.move YA hereda de mail.thread por defecto en Odoo

    ai_invoice_file = fields.Binary(
        string="AI Invoice File",
        help="Upload invoice file to analyze with AI",
        copy=False,
    )
    ai_invoice_filename = fields.Char(string="AI Filename", copy=False)

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

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Invoice data has been successfully imported from AI."),
                    "type": "success",
                    "sticky": False,
                },
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

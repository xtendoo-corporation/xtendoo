# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Campos para alias de email
    ai_invoice_alias_enabled = fields.Boolean(
        string="Enable Email Invoice Import",
        default=False,
        help="Enable automatic invoice import from emails sent to this journal's alias",
    )
    ai_invoice_alias_id = fields.Many2one(
        "mail.alias",
        string="Email Alias",
        ondelete="restrict",
        help="Email alias for receiving invoices (e.g., invoices@mycompany.odoo.com)",
    )
    ai_invoice_alias_name = fields.Char(
        related="ai_invoice_alias_id.alias_name",
        string="Alias Name",
        readonly=False,
    )
    ai_invoice_create_partner = fields.Boolean(
        string="Auto-create Partners",
        default=True,
        help="Automatically create supplier if not found in the system",
    )
    ai_invoice_attach_original = fields.Boolean(
        string="Attach Original File",
        default=True,
        help="Attach the original invoice file to the created invoice",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Crear alias al crear el diario si está habilitado"""
        journals = super().create(vals_list)
        for journal, vals in zip(journals, vals_list):
            if vals.get("ai_invoice_alias_enabled") and not journal.ai_invoice_alias_id:
                journal._create_ai_invoice_alias()
        return journals

    def write(self, vals):
        """Crear/eliminar alias al activar/desactivar"""
        res = super().write(vals)
        if "ai_invoice_alias_enabled" in vals:
            for journal in self:
                if journal.ai_invoice_alias_enabled and not journal.ai_invoice_alias_id:
                    journal._create_ai_invoice_alias()
                elif (
                    not journal.ai_invoice_alias_enabled and journal.ai_invoice_alias_id
                ):
                    # No eliminamos el alias, solo lo desactivamos
                    journal.ai_invoice_alias_id.write({"alias_name": False})
        return res

    def _create_ai_invoice_alias(self):
        """Crear alias de email para recibir facturas"""
        self.ensure_one()

        if self.ai_invoice_alias_id:
            return self.ai_invoice_alias_id

        # Generar nombre de alias basado en el código del diario
        alias_name = f"invoices-{self.code.lower()}" if self.code else "invoices"

        alias_vals = {
            "alias_name": alias_name,
            "alias_model_id": self.env["ir.model"]._get("account.journal").id,
            "alias_parent_model_id": self.env["ir.model"]._get("account.journal").id,
            "alias_parent_thread_id": self.id,
            "alias_defaults": "{}",
            "alias_force_thread_id": self.id,
        }

        alias = self.env["mail.alias"].create(alias_vals)
        self.ai_invoice_alias_id = alias.id

        _logger.info(f"Created email alias '{alias_name}' for journal {self.name}")
        return alias

    def message_new(self, msg_dict, custom_values=None):
        """
        Procesar emails entrantes con facturas adjuntas.
        Este método se llama cuando llega un email al alias.
        """
        _logger.info(
            f"Received email for journal alias: {msg_dict.get('subject', 'No subject')}"
        )

        # Si no está habilitado, usar comportamiento por defecto
        if not self.ai_invoice_alias_enabled:
            return super().message_new(msg_dict, custom_values=custom_values)

        # Procesar adjuntos de facturas
        self._process_invoice_attachments_from_email(msg_dict)

        # No crear ningún registro adicional, solo retornar el journal
        return self

    def message_update(self, msg_dict, update_vals=None):
        """
        Procesar emails de seguimiento (respuestas).
        """
        _logger.info(
            f"Received follow-up email for journal: {msg_dict.get('subject', 'No subject')}"
        )

        if self.ai_invoice_alias_enabled:
            self._process_invoice_attachments_from_email(msg_dict)

        return super().message_update(msg_dict, update_vals=update_vals)

    def _process_invoice_attachments_from_email(self, msg_dict):
        """
        Extraer y procesar adjuntos de facturas del email.
        """
        self.ensure_one()

        attachments = msg_dict.get("attachments", [])
        if not attachments:
            _logger.info("No attachments found in email")
            return

        _logger.info(f"Processing {len(attachments)} attachments from email")

        processed_count = 0
        error_count = 0

        for attachment in attachments:
            try:
                filename = attachment[0]
                file_content = attachment[1]

                # Validar tipo de archivo
                if not self._is_valid_invoice_file(filename):
                    _logger.info(f"Skipping non-invoice file: {filename}")
                    continue

                _logger.info(f"Processing invoice file: {filename}")

                # Crear factura usando el wizard de IA
                self._create_invoice_from_attachment(filename, file_content, msg_dict)
                processed_count += 1

            except Exception as e:
                _logger.error(
                    f"Error processing attachment {filename}: {str(e)}", exc_info=True
                )
                error_count += 1

        # Enviar notificación al remitente
        if processed_count > 0 or error_count > 0:
            self._send_processing_notification(
                msg_dict.get("email_from"),
                processed_count,
                error_count,
                msg_dict.get("message_id"),
            )

    def _is_valid_invoice_file(self, filename):
        """Verificar si el archivo es un tipo válido para facturas"""
        if not filename:
            return False

        filename_lower = filename.lower()
        valid_extensions = (".pdf", ".jpg", ".jpeg", ".png")
        return filename_lower.endswith(valid_extensions)

    def _create_invoice_from_attachment(self, filename, file_content, msg_dict):
        """
        Crear factura borrador usando el wizard de IA.
        """
        self.ensure_one()

        # Crear wizard
        wizard = self.env["xtendoo.invoice.ai.wizard"].create(
            {
                "upload": file_content,
                "filename": filename,
                "company_id": self.company_id.id,
                "journal_id": self.id,
                "create_partner_if_missing": self.ai_invoice_create_partner,
                "attach_original": self.ai_invoice_attach_original,
            }
        )

        # Procesar con IA
        result = wizard.action_process_invoice()

        # Si se creó una factura, añadir información del email
        if result.get("res_id"):
            invoice = self.env["account.move"].browse(result["res_id"])

            # Añadir nota con información del email
            email_from = msg_dict.get("email_from", "Unknown")
            subject = msg_dict.get("subject", "No subject")

            note = _(
                "📧 Invoice received by email\n"
                "From: %s\n"
                "Subject: %s\n"
                "Processed automatically with AI"
            ) % (email_from, subject)

            current_narration = invoice.narration or ""
            invoice.narration = (
                current_narration + "\n\n" + note if current_narration else note
            )

            _logger.info(
                f"Created invoice {invoice.name} from email attachment {filename}"
            )

    def _send_processing_notification(
        self, email_to, success_count, error_count, in_reply_to=None
    ):
        """
        Enviar notificación por email sobre el resultado del procesamiento.
        """
        if not email_to:
            return

        self.ensure_one()

        subject = _("Invoice Processing Result - %s") % self.name

        if error_count == 0:
            body = (
                _(
                    "<p>Your invoice(s) have been successfully processed:</p>"
                    "<ul>"
                    "<li>✅ Successfully processed: <strong>%s</strong> invoice(s)</li>"
                    "</ul>"
                    "<p>The draft invoice(s) are now available in the system for review.</p>"
                )
                % success_count
            )
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

        if in_reply_to:
            mail_values["reply_to"] = self.ai_invoice_alias_id.display_name
            mail_values["headers"] = {"In-Reply-To": in_reply_to}

        try:
            mail = self.env["mail.mail"].create(mail_values)
            mail.send()
            _logger.info(f"Sent processing notification to {email_to}")
        except Exception as e:
            _logger.error(f"Failed to send notification email: {str(e)}")

    def action_open_ai_import_wizard(self):
        """Abrir wizard de importación de facturas con IA desde el dashboard del diario"""
        self.ensure_one()

        return {
            "name": "Importar Factura con IA (OCR)",
            "type": "ir.actions.act_window",
            "res_model": "xtendoo.invoice.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_id": self.company_id.id,
                "default_journal_id": self.id,
                "default_create_partner_if_missing": True,
                "default_attach_original": True,
            },
        }

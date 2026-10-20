# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class WhatsappComposer(models.TransientModel):
    _inherit = "whatsapp.composer"

    # Attachment support
    attachment_id = fields.Many2one(
        'ir.attachment',
        string="Attachment",
        help="Attach a file to send with the WhatsApp message (PDF, images, etc.)"
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_composer_attachment_rel',
        'composer_id',
        'attachment_id',
        string="Attachments",
        help="Multiple attachments to send with the message"
    )


    @api.model
    def default_get(self, fields_list):
        """Override to auto-attach PDF for sales orders and invoices"""
        import logging
        _logger = logging.getLogger(__name__)

        res = super().default_get(fields_list)

        # Solo procesar si tenemos res_model y res_id
        res_model = res.get('res_model')
        res_id = res.get('res_id')

        _logger.info(f"WhatsApp Composer default_get: model={res_model}, id={res_id}")

        if res_model and res_id:
            # Auto-generar PDF para ventas y facturas
            if res_model in ['sale.order', 'account.move']:
                try:
                    record = self.env[res_model].browse(res_id)
                    if record.exists():
                        _logger.info(f"Generating PDF for {res_model} {record.id}")
                        pdf_attachment = self._generate_pdf_for_record(record)
                        if pdf_attachment:
                            _logger.info(f"PDF generated successfully: {pdf_attachment.name} (ID: {pdf_attachment.id})")
                            res['attachment_ids'] = [(6, 0, [pdf_attachment.id])]
                        else:
                            _logger.warning(f"Could not generate PDF for {res_model} {record.id}")
                except Exception as e:
                    _logger.error(f"Error auto-generating PDF for {res_model}: {e}", exc_info=True)

        return res

    @api.model
    def _generate_pdf_for_record(self, record):
        """Generate PDF attachment for sale.order or account.move"""
        import logging
        import base64
        _logger = logging.getLogger(__name__)

        try:
            report_name = None
            filename = None

            if record._name == 'sale.order':
                # Determinar el nombre del reporte según el estado
                report_name = 'sale.action_report_saleorder'
                filename = f"Quotation_{record.name}.pdf"
                if record.state in ['sale', 'done']:
                    filename = f"Order_{record.name}.pdf"

            elif record._name == 'account.move':
                # Solo para facturas de cliente
                if record.move_type in ['out_invoice', 'out_refund']:
                    report_name = 'account.account_invoices'
                    filename = f"Invoice_{record.name}.pdf"
                    if record.move_type == 'out_refund':
                        filename = f"Refund_{record.name}.pdf"
                else:
                    return None

            if not report_name or not filename:
                return None

            # Obtener el reporte por su xmlid
            _logger.info(f"Looking for report: {report_name}")
            report = self.env.ref(report_name, raise_if_not_found=False)

            if not report:
                _logger.warning(f"Report {report_name} not found")
                return None

            # Generar el PDF usando _render directamente para evitar problemas con industry_fsm
            _logger.info(f"Rendering PDF for {record._name} {record.id}")

            # Usar report_action y extraer el PDF del resultado
            # Este es el método más robusto que funciona siempre
            pdf_content = report.sudo()._render_qweb_pdf(report.id, record.ids)[0]

            # Crear el attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': record._name,
                'res_id': record.id,
                'mimetype': 'application/pdf',
            })

            _logger.info(f"✅ Auto-generated PDF: {attachment.name} (ID: {attachment.id})")
            return attachment

        except Exception as e:
            _logger.error(f"❌ Error generating PDF for {record._name} {record.id}: {e}", exc_info=True)

        return None


    def _action_send_whatsapp(self):
        """Send WhatsApp message with optional attachments."""
        import logging
        _logger = logging.getLogger(__name__)

        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return

        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)

        # Prepare context with template and variables
        # default_res_id is needed by OCA's prepare_value_to_send() to resolve variables
        ctx = {
            'whatsapp_template_id': self.template_id.id if self.template_id else False,
            'default_res_id': self.res_id,
            'default_res_model': self.res_model,
        }

        # Prepare attachments - we need to copy them to link to the new message
        attachment_ids = []
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                # Create a copy of the attachment linked to the channel
                new_attachment = attachment.copy({
                    'res_model': 'discuss.channel',
                    'res_id': channel.id,
                })
                attachment_ids.append(new_attachment.id)
            _logger.info(f"Prepared {len(attachment_ids)} attachments for WhatsApp message")

        # Send message - message_post will create a mail.message with attachment_ids
        message = channel.with_context(**ctx).message_post(
            body=self.body,
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
            attachment_ids=attachment_ids if attachment_ids else []
        )

        _logger.info(f"Message posted to channel with {len(message.attachment_ids)} attachments")

        # === NUEVA FUNCIONALIDAD: Gestión de confirmaciones pendientes ===
        # Si la plantilla requiere confirmación, crear un registro pendiente
        if self.template_id and self.template_id.requires_confirmation and self.template_id.confirmation_template_id:
            try:
                # Obtener el partner del canal
                partner = None
                if hasattr(channel, 'channel_partner_ids') and channel.channel_partner_ids:
                    partners = channel.channel_partner_ids.filtered(
                        lambda p: p.id != self.env.ref('base.partner_root').id and p.id != self.env.user.partner_id.id
                    )
                    if partners:
                        partner = partners[0]

                if partner:
                    # Cancelar confirmaciones pendientes anteriores para este partner y canal
                    self.env['whatsapp.pending.confirmation'].search([
                        ('partner_id', '=', partner.id),
                        ('channel_id', '=', channel.id),
                        ('state', '=', 'waiting')
                    ]).write({'state': 'cancelled'})

                    # Crear nuevo registro de confirmación pendiente
                    pending = self.env['whatsapp.pending.confirmation'].create({
                        'partner_id': partner.id,
                        'channel_id': channel.id,
                        'template_id': self.template_id.id,
                        'confirmation_template_id': self.template_id.confirmation_template_id.id,
                        'res_model': self.res_model,
                        'res_id': self.res_id,
                        'confirmation_type': self.template_id.confirmation_type,
                        'state': 'waiting',
                    })

                    _logger.info(f"✅ Created pending confirmation {pending.id} - waiting for response from {partner.name}")
                    _logger.info(f"   Will send template '{self.template_id.confirmation_template_id.name}' on confirmation")
                else:
                    _logger.warning("⚠️ Could not identify partner for pending confirmation")

            except Exception as e:
                _logger.error(f"❌ Error creating pending confirmation: {e}", exc_info=True)
        # === FIN NUEVA FUNCIONALIDAD ===

        # Registrar también en el contacto destinatario si existe
        partner = None
        if hasattr(channel, 'channel_partner_ids') and channel.channel_partner_ids:
            partners = channel.channel_partner_ids.filtered(
                lambda p: p.id != self.env.ref('base.partner_root').id and p.id != self.env.user.partner_id.id
            )
            if partners:
                partner = partners[0]

        if partner:
            # Also copy attachments for partner message
            partner_attachment_ids = []
            if self.attachment_ids:
                for attachment in self.attachment_ids:
                    partner_attachment = attachment.copy({
                        'res_model': 'res.partner',
                        'res_id': partner.id,
                    })
                    partner_attachment_ids.append(partner_attachment.id)

            partner.sudo().message_post(
                body=self.body,
                author_id=self.env.user.partner_id.id,
                gateway_type="whatsapp",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                attachment_ids=partner_attachment_ids if partner_attachment_ids else []
            )


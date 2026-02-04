from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class BookingRequest(models.Model):
    _inherit = 'booking.request'

    def _phone_get_number_fields(self):
        """Return the fields that contain phone numbers for this model."""
        return ['phone']

    whatsapp_opt_in = fields.Boolean(string="WhatsApp Opt-In", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to update partner's whatsapp_opt_in immediately."""
        records = super().create(vals_list)

        for record in records:
            # Actualizar partner inmediatamente al crear la solicitud
            if record.phone or record.email:
                partner = self._find_partner_for_request(record)
                if partner and partner.whatsapp_opt_in != record.whatsapp_opt_in:
                    partner.sudo().write({'whatsapp_opt_in': record.whatsapp_opt_in})
                    _logger.info(
                        "Partner '%s' (ID: %s) whatsapp_opt_in actualizado a %s desde solicitud ID: %s (create)",
                        partner.name, partner.id, record.whatsapp_opt_in, record.id
                    )

        return records

    def write(self, vals):
        """Override write to update partner's whatsapp_opt_in when modified."""
        res = super().write(vals)

        # Si se modificó whatsapp_opt_in, actualizar el partner
        if 'whatsapp_opt_in' in vals:
            for record in self:
                if record.phone or record.email:
                    partner = self._find_partner_for_request(record)
                    if partner and partner.whatsapp_opt_in != record.whatsapp_opt_in:
                        partner.sudo().write({'whatsapp_opt_in': record.whatsapp_opt_in})
                        _logger.info(
                            "Partner '%s' (ID: %s) whatsapp_opt_in actualizado a %s desde solicitud ID: %s (write)",
                            partner.name, partner.id, record.whatsapp_opt_in, record.id
                        )

        return res

    def _find_partner_for_request(self, record):
        """Buscar partner existente por email o teléfono."""
        Partner = self.env['res.partner'].sudo()
        partner = False

        # Buscar por email
        if record.email:
            partner = Partner.search([('email', '=', record.email)], limit=1)

        # Si no se encontró por email, buscar por teléfono
        if not partner and record.phone:
            # Limpiar formato del teléfono para búsqueda
            phone_clean = record.phone.replace(' ', '').replace('+', '')
            partner = Partner.search([
                '|', ('phone', 'ilike', phone_clean),
                ('mobile', 'ilike', phone_clean)
            ], limit=1)

        return partner

    def _get_or_create_partner(self):
        partner = super()._get_or_create_partner()
        # Siempre actualizar el whatsapp_opt_in del partner según la solicitud
        if partner.whatsapp_opt_in != self.whatsapp_opt_in:
            partner.sudo().write({'whatsapp_opt_in': self.whatsapp_opt_in})
        return partner

    def action_approve(self):
        res = super().action_approve()
        if self.whatsapp_opt_in:
            self._send_whatsapp_notification('Cita Aprobada WhatsApp')
        return res

    def action_reject(self):
        res = super().action_reject()
        if self.whatsapp_opt_in:
            self._send_whatsapp_notification('Cita Rechazada WhatsApp')
        return res

    def _send_whatsapp_notification(self, template_name):
        """Send WhatsApp notification using the given template."""
        _logger.info("Intentando enviar WhatsApp con template nombre: %s para solicitud ID: %s", template_name, self.id)

        # Buscar template por nombre en lugar de xmlid
        template = self.env['mail.whatsapp.template'].search([
            ('name', '=', template_name),
            ('model_id.model', '=', 'booking.request')
        ], limit=1)

        if not template:
            _logger.warning("Template WhatsApp no encontrado con nombre: %s", template_name)
            return

        _logger.info("Template WhatsApp encontrado: %s (ID: %s)", template.name, template.id)

        try:
            gateway = self.env['mail.gateway'].search([
                ('gateway_type', '=', 'whatsapp'),
                ('active', '=', True)
            ], limit=1)

            if not gateway:
                _logger.error("No hay gateway WhatsApp activo configurado")
                return

            _logger.info("Gateway WhatsApp encontrado: %s (ID: %s)", gateway.name, gateway.id)

            # Ensure channel exists using method from mail_gateway_whatsapp_chatter inheritance
            if not hasattr(self, '_whatsapp_get_channel'):
                _logger.error("Método _whatsapp_get_channel no disponible en booking.request")
                return

            try:
                channel = self._whatsapp_get_channel('phone', gateway)
                if not channel:
                    _logger.error("No se pudo crear canal WhatsApp para solicitud ID: %s", self.id)
                    return

                _logger.info("Canal WhatsApp creado correctamente para: %s", self.phone)

                # Render body manually (simple variable substitution)
                body = template.body
                if template.variable_ids:
                    for var in template.variable_ids:
                        value = ''
                        if var.field_type == 'field' and var.field_name:
                            # Start with self
                            record_val = self
                            try:
                                for field_part in var.field_name.split('.'):
                                    if record_val:
                                        record_val = record_val[field_part]
                                value = str(record_val) if record_val else ''
                            except Exception as e_var:
                                _logger.warning("Error al obtener variable %s: %s", var.name, str(e_var))
                                value = ''
                        elif var.field_type == 'user_name':
                            value = self.env.user.name
                        elif var.field_type == 'user_mobile':
                            value = self.env.user.mobile or self.env.user.phone or ''

                        # Replace {{var_X}}
                        body = body.replace(var.name, value)

                _logger.info("Mensaje WhatsApp renderizado, enviando...")

                # Send message
                # Pass whatsapp_template_id in context so gateway knows it's a template
                channel.with_context(whatsapp_template_id=template.id).message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid="mail.mt_comment",
                    author_id=self.env.user.partner_id.id
                )

                _logger.info("WhatsApp enviado correctamente a %s para solicitud ID: %s", self.phone, self.id)

            except Exception as e_channel:
                _logger.error("Error al crear/enviar por canal WhatsApp: %s", str(e_channel), exc_info=True)

        except Exception as e:
            _logger.error("Error general al enviar WhatsApp para solicitud ID %s: %s", self.id, str(e), exc_info=True)

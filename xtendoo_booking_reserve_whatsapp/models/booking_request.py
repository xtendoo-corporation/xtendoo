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
            self._send_whatsapp_notification('xtendoo_booking_reserve_whatsapp.email_template_booking_whatsapp_approved')
        return res

    def action_reject(self):
        res = super().action_reject()
        if self.whatsapp_opt_in:
            self._send_whatsapp_notification('xtendoo_booking_reserve_whatsapp.email_template_booking_whatsapp_rejected')
        return res

    def _send_whatsapp_notification(self, template_xmlid):
        """Send WhatsApp notification using the given template."""
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return

        try:
            gateway = self.env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
            if gateway:
                # Ensure channel exists using method from mail_gateway_whatsapp_chatter inheritance
                if hasattr(self, '_whatsapp_get_channel'):
                    channel = self._whatsapp_get_channel('phone', gateway)

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
                                except Exception:
                                    value = ''
                            elif var.field_type == 'user_name':
                                value = self.env.user.name
                            elif var.field_type == 'user_mobile':
                                value = self.env.user.mobile or self.env.user.phone or ''

                            # Replace {{var_X}}
                            body = body.replace(var.name, value)

                    # Send message
                    # Pass whatsapp_template_id in context so gateway knows it's a template
                    channel.with_context(whatsapp_template_id=template.id).message_post(
                        body=body,
                        message_type='comment',
                        subtype_xmlid="mail.mt_comment",
                        author_id=self.env.user.partner_id.id
                    )
        except Exception as e:
            # Log error but don't crash the checking flow
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error sending WhatsApp: {e}")

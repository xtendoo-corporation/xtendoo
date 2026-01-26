from odoo import models,fields

class BookingRequest(models.Model):
    _inherit = 'booking.request'

    def _phone_get_number_fields(self):
        """Return the fields that contain phone numbers for this model."""
        return ['phone']

    whatsapp_opt_in = fields.Boolean(string="WhatsApp Opt-In", default=False)

    def _get_or_create_partner(self):
        partner = super()._get_or_create_partner()
        if self.whatsapp_opt_in and not partner.whatsapp_opt_in:
            partner.sudo().write({'whatsapp_opt_in': True})
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

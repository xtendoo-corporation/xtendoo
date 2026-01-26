from odoo import api, models, fields

class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _send_reminder(self):
        """Handle WhatsApp alarms in addition to standard ones."""
        # Call super to handle email reminders
        super()._send_reminder()

        # Handle WhatsApp reminders
        events_by_alarm = self._get_events_by_alarm_to_notify('whatsapp')
        if not events_by_alarm:
            return

        for alarm_id, event_ids in events_by_alarm.items():
            alarm = self.env['calendar.alarm'].browse(alarm_id)
            events = self.env['calendar.event'].browse(event_ids)
            
            for event in events:
                # Filter partners who accepted/needs action AND have opted in for WhatsApp
                partners = event.attendee_ids.filtered(
                    lambda a: a.state != 'declined' and a.partner_id.whatsapp_opt_in
                ).partner_id
                
                for partner in partners:
                    self._send_whatsapp_event_reminder(event, partner, alarm.whatsapp_template_id)

    def _send_whatsapp_event_reminder(self, event, partner, template):
        """Send a single WhatsApp reminder for an event."""
        if not template:
            return
            
        try:
            gateway = self.env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
            if not gateway:
                return

            # Note: We need a phone number. event usually has partners. 
            # partner should have 'phone' or 'mobile'.
            
            # Using the logic from our booking_request override (adapted for event/partner context)
            if hasattr(event, '_whatsapp_get_channel'):
                # We need to ensure we target the RIGHT partner. 
                # _whatsapp_get_channel on a 'calendar.event' might be complex if it doesn't know which partner.
                # However, mail_gateway_whatsapp_chatter defines it on mail.thread.
                
                # Usually we want to get channel for the PARTNER.
                # If mail.thread override exists:
                channel = partner._whatsapp_get_channel('mobile', gateway) or partner._whatsapp_get_channel('phone', gateway)
                
                if channel:
                    # Render body (simplified manual replacement for events)
                    # Ideally we would use a more robust renderer but following simple pattern
                    body = template.body
                    # Basic variables common for events
                    replacements = {
                        '{{1}}': partner.name,
                        '{{2}}': event.name,
                        '{{3}}': str(event.start),
                    }
                    # Also support the {{var_1}} structure if used in templates
                    if template.variable_ids:
                         for var in template.variable_ids:
                            # Try to extract from event
                            val = ''
                            if var.field_type == 'field' and var.field_name:
                                try:
                                    v = event
                                    for p in var.field_name.split('.'):
                                        v = v[p]
                                    val = str(v) if v else ''
                                except Exception: pass
                            
                            if val:
                                body = body.replace(var.name, val)
                    
                    # Fallback replacements
                    for key, val in replacements.items():
                        body = body.replace(key, val)

                    channel.with_context(whatsapp_template_id=template.id).message_post(
                        body=body,
                        message_type='comment',
                        subtype_xmlid="mail.mt_comment",
                        author_id=self.env.user.partner_id.id
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send calendar WA reminder: {e}")

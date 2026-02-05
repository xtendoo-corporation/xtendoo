from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


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

        now = fields.Datetime.now()

        for alarm_id, event_ids in events_by_alarm.items():
            alarm = self.env['calendar.alarm'].browse(alarm_id)
            events = self.env['calendar.event'].browse(event_ids)

            # Validate alarm has template configured
            if not alarm.whatsapp_template_id:
                _logger.warning(
                    "WhatsApp alarm '%s' (ID: %s) has no template configured. Skipping.",
                    alarm.name, alarm.id
                )
                continue

            # Filter only active events (not ended yet)
            active_events = events.filtered(lambda e: e.stop > now)

            for event in active_events:
                # Filter partners who accepted/needs action AND have opted in for WhatsApp
                partners = event.attendee_ids.filtered(
                    lambda a: a.state != 'declined' and a.partner_id.whatsapp_opt_in
                ).partner_id

                if not partners:
                    _logger.debug(
                        "Event '%s' (ID: %s) has no partners with WhatsApp opt-in. Skipping.",
                        event.name, event.id
                    )
                    continue

                for partner in partners:
                    self._send_whatsapp_event_reminder(event, partner, alarm.whatsapp_template_id)

                # Schedule next reminder if it's a recurring event
                if event.recurrence_id:
                    from datetime import timedelta
                    next_date = event.get_next_alarm_date(events_by_alarm)
                    if next_date:
                        cron = self.env.ref('calendar.ir_cron_scheduler_alarm')
                        cron._trigger(at=next_date - timedelta(minutes=alarm.duration_minutes))

    def _send_whatsapp_event_reminder(self, event, partner, template):
        """Send a single WhatsApp reminder for an event."""
        if not template:
            _logger.warning("No template provided for WhatsApp reminder. Skipping.")
            return

        # Validate partner has phone number
        if not partner.mobile and not partner.phone:
            _logger.debug(
                "Partner '%s' (ID: %s) has no phone number. Skipping WhatsApp reminder.",
                partner.name, partner.id
            )
            return

        try:
            # Obtener gateway desde el template de la alarma
            gateway = alarm.whatsapp_template_id.gateway_id if alarm.whatsapp_template_id else None

            if not gateway:
                _logger.error(
                    "No WhatsApp gateway found in template. Cannot send reminder for event '%s' (ID: %s).",
                    event.name, event.id
                )
                return

            # Using the logic from our booking_request override (adapted for event/partner context)
            # Try to get channel using partner's phone numbers
            channel = None
            if hasattr(partner, '_whatsapp_get_channel'):
                channel = partner._whatsapp_get_channel('mobile', gateway) or partner._whatsapp_get_channel('phone', gateway)

            if not channel:
                _logger.warning(
                    "Could not create WhatsApp channel for partner '%s' (ID: %s). Skipping.",
                    partner.name, partner.id
                )
                return

            # Render body (simplified manual replacement for events)
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
                        except Exception:
                            pass

                    if val:
                        body = body.replace(var.name, val)

            # Fallback replacements
            for key, val in replacements.items():
                body = body.replace(key, val)

            # Send message via channel with context for variable extraction
            channel.with_context(
                whatsapp_template_id=template.id,
                active_id=event.id,           # Pass event ID for variable extraction
                active_model='calendar.event'  # Pass the model name
            ).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid="mail.mt_comment",
                author_id=self.env.user.partner_id.id
            )

            _logger.info(
                "WhatsApp reminder sent to '%s' (ID: %s) for event '%s' (ID: %s)",
                partner.name, partner.id, event.name, event.id
            )

        except Exception as e:
            _logger.error(
                "Failed to send WhatsApp reminder to '%s' (ID: %s) for event '%s' (ID: %s): %s",
                partner.name, partner.id, event.name, event.id, str(e)
            )

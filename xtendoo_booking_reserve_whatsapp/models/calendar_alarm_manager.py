from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    def _get_events_by_alarm_to_notify(self, alarm_type='whatsapp'):
        """Get events that need WhatsApp alarm notification.

        Returns a dict: {alarm_id: [event_ids]}
        """
        result = {}

        # Get all alarms of the specified type
        alarms = self.env['calendar.alarm'].search([('alarm_type', '=', alarm_type)])

        if not alarms:
            return result

        now = fields.Datetime.now()

        for alarm in alarms:
            # Calculate the notification time
            # alarm.duration is a number (1, 2, etc)
            # alarm.interval is the unit ('days', 'hours', 'minutes')
            from datetime import timedelta

            if alarm.interval == 'minutes':
                delta = timedelta(minutes=alarm.duration)
            elif alarm.interval == 'hours':
                delta = timedelta(hours=alarm.duration)
            elif alarm.interval == 'days':
                delta = timedelta(days=alarm.duration)
            else:
                continue  # Unknown interval

            # Find events that:
            # 1. Have this alarm assigned
            # 2. Start time - alarm duration <= now < start time
            # 3. Haven't been notified yet (we'll check this later)

            # Calculate the notification window
            # Events starting between now and now + 1 day should trigger alarms
            notification_start = now
            notification_end = now + timedelta(days=2)  # Check 2 days ahead

            events = self.env['calendar.event'].search([
                ('alarm_ids', 'in', alarm.id),
                ('start', '>=', notification_start),
                ('start', '<=', notification_end),
                ('stop', '>', now),  # Event not ended yet
            ])

            # Filter events where the alarm should trigger
            events_to_notify = []
            for event in events:
                # Calculate when the alarm should fire
                alarm_time = event.start - delta

                # If alarm_time is in the past or now, it should trigger
                if alarm_time <= now:
                    events_to_notify.append(event.id)

            if events_to_notify:
                result[alarm.id] = events_to_notify

        return result

    @api.model
    def _send_reminder(self):
        """Handle WhatsApp alarms in addition to standard ones."""
        _logger.info("=" * 80)
        _logger.info("INICIO _send_reminder() para WhatsApp")
        _logger.info("=" * 80)

        # Call super to handle email reminders
        super()._send_reminder()

        # Handle WhatsApp reminders
        _logger.info("→ Buscando eventos con alarmas WhatsApp pendientes...")

        # Debug: ver todas las alarmas WhatsApp
        all_whatsapp_alarms = self.env['calendar.alarm'].search([('alarm_type', '=', 'whatsapp')])
        _logger.info("  Total de alarmas WhatsApp en el sistema: %d", len(all_whatsapp_alarms))
        for alarm in all_whatsapp_alarms:
            _logger.info("    - Alarma ID %s: '%s' (Duración: %s %s)",
                        alarm.id, alarm.name, alarm.duration, alarm.interval)

        # Debug: ver todos los eventos con alarmas WhatsApp
        events_with_whatsapp_alarms = self.env['calendar.event'].search([
            ('alarm_ids.alarm_type', '=', 'whatsapp'),
            ('stop', '>', fields.Datetime.now())
        ])
        _logger.info("  Total de eventos activos con alarmas WhatsApp: %d", len(events_with_whatsapp_alarms))
        for event in events_with_whatsapp_alarms:
            _logger.info("    - Evento ID %s: '%s' (Start: %s, Alarmas: %s)",
                        event.id, event.name, event.start, event.alarm_ids.mapped('name'))

        events_by_alarm = self._get_events_by_alarm_to_notify('whatsapp')

        if not events_by_alarm:
            _logger.info("⚠️ No se encontraron eventos con alarmas WhatsApp pendientes")
            _logger.info("=" * 80)
            return

        _logger.info("✓ Encontrados eventos para %d alarmas WhatsApp", len(events_by_alarm))

        now = fields.Datetime.now()
        _logger.info("Fecha/hora actual: %s", now)

        for alarm_id, event_ids in events_by_alarm.items():
            alarm = self.env['calendar.alarm'].browse(alarm_id)
            events = self.env['calendar.event'].browse(event_ids)

            _logger.info("")
            _logger.info("→ Procesando alarma ID %s: '%s'", alarm_id, alarm.name)
            _logger.info("  Eventos a notificar: %s (IDs: %s)", len(event_ids), event_ids)

            # Validate alarm has template configured
            if not alarm.whatsapp_template_id:
                _logger.warning(
                    "⚠️ Alarma WhatsApp '%s' (ID: %s) NO tiene plantilla configurada. Saltando.",
                    alarm.name, alarm.id
                )
                continue

            _logger.info("  ✓ Plantilla configurada: %s (ID: %s)",
                        alarm.whatsapp_template_id.name, alarm.whatsapp_template_id.id)

            # Filter only active events (not ended yet)
            active_events = events.filtered(lambda e: e.stop > now)
            _logger.info("  Eventos activos (no finalizados): %d de %d", len(active_events), len(events))

            for event in active_events:
                _logger.info("")
                _logger.info("  → Procesando evento ID %s: '%s'", event.id, event.name)
                _logger.info("    Start: %s, Stop: %s", event.start, event.stop)
                _logger.info("    Asistentes totales: %d", len(event.attendee_ids))

                # Filter partners who accepted/needs action AND have opted in for WhatsApp
                partners = event.attendee_ids.filtered(
                    lambda a: a.state != 'declined' and a.partner_id.whatsapp_opt_in
                ).partner_id

                _logger.info("    Asistentes con WhatsApp opt-in: %d", len(partners))

                if not partners:
                    _logger.info(
                        "    ⚠️ Evento '%s' (ID: %s) no tiene asistentes con WhatsApp opt-in. Saltando.",
                        event.name, event.id
                    )
                    continue

                _logger.info("    ✓ Enviando recordatorios a: %s", ', '.join(partners.mapped('name')))

                for partner in partners:
                    self._send_whatsapp_event_reminder(event, partner, alarm.whatsapp_template_id)

                # Schedule next reminder if it's a recurring event
                if event.recurrence_id:
                    from datetime import timedelta
                    next_date = event.get_next_alarm_date(events_by_alarm)
                    if next_date:
                        cron = self.env.ref('calendar.ir_cron_scheduler_alarm')
                        cron._trigger(at=next_date - timedelta(minutes=alarm.duration_minutes))

        _logger.info("")
        _logger.info("=" * 80)
        _logger.info("FIN _send_reminder() para WhatsApp")
        _logger.info("=" * 80)

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
            # Obtener gateway desde el template
            gateway = template.gateway_id if template else None

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

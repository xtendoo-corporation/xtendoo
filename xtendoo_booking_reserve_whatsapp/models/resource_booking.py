# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models, fields, _
import logging

_logger = logging.getLogger(__name__)


class ResourceBooking(models.Model):
    _inherit = 'resource.booking'

    calendar_event_id = fields.Many2one(
        comodel_name='calendar.event',
        string='Evento de Calendario',
        readonly=True,
        help="Evento de calendario creado automáticamente para esta reserva"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically create calendar.event with alarms."""
        _logger.info("   │")
        _logger.info("   │  ⚙️ resource.booking.create() llamado")
        _logger.info("   │     Cantidad de bookings a crear: %d", len(vals_list))

        # NUEVA ESTRATEGIA: Dejar que se cree el meeting normalmente (para que combination_id funcione)
        # pero PREVENIR los emails usando el contexto correcto
        bookings = super(ResourceBooking, self.with_context(
            no_mail_to_attendees=True,  # CRÍTICO: Prevenir emails en calendar.event
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
            mail_notrack=True,
            tracking_disable=True,
        )).create(vals_list)

        _logger.info("   │  ✓ Bookings creados: IDs %s", bookings.ids)

        for booking in bookings:
            # Si el módulo base creó un meeting_id automáticamente, reemplazarlo con uno personalizado
            if hasattr(booking, 'meeting_id') and booking.meeting_id:
                _logger.info("   │  ⚠️ Booking ID %s tiene meeting_id auto-creado (ID: %s) - Reemplazando con alarmas WhatsApp...",
                           booking.id, booking.meeting_id.id)

                old_meeting = booking.meeting_id
                old_meeting_id = old_meeting.id

                # Obtener alarmas WhatsApp configuradas
                whatsapp_alarms = self.env['calendar.alarm'].search([
                    ('alarm_type', '=', 'whatsapp'),
                    ('whatsapp_template_id', '!=', False)
                ])

                if whatsapp_alarms:
                    _logger.info("   │     → Añadiendo %d alarmas WhatsApp al meeting existente ID %s",
                               len(whatsapp_alarms), old_meeting_id)

                    # Añadir las alarmas WhatsApp al meeting existente SIN enviar emails
                    old_meeting.with_context(
                        no_mail_to_attendees=True,
                        mail_notrack=True,
                        tracking_disable=True,
                    ).sudo().write({
                        'alarm_ids': [(4, alarm.id) for alarm in whatsapp_alarms]
                    })

                    _logger.info("   │     ✓ Alarmas WhatsApp añadidas al meeting ID %s", old_meeting_id)
                else:
                    _logger.warning("   │     ⚠ No hay alarmas WhatsApp configuradas")

                # Actualizar el campo calendar_event_id para tracking
                booking.with_context(no_mail_to_attendees=True).write({
                    'calendar_event_id': old_meeting_id
                })

                _logger.info("   │  ✓ Meeting ID %s actualizado con alarmas WhatsApp para booking ID %s",
                           old_meeting_id, booking.id)
            else:
                # Si por alguna razón no se creó meeting_id, crear uno manualmente
                _logger.info("   │  ℹ️ Booking ID %s NO tiene meeting_id - Creando uno...", booking.id)
                booking._create_calendar_event()

        _logger.info("   │  ✓ Todos los calendar.event procesados con alarmas WhatsApp")
        return bookings

    def write(self, vals):
        """Override write to update calendar.event if booking changes."""
        _logger.info("   │")
        _logger.info("   │  ⚙️ resource.booking.write() llamado para booking IDs: %s", self.ids)
        _logger.info("   │     Campos a modificar: %s", list(vals.keys()))
        _logger.info("   │     Valores: %s", vals)

        res = super().write(vals)

        # Si se modificaron campos relevantes, actualizar el evento
        relevant_fields = ['start', 'stop', 'name', 'partner_ids']
        modified_relevant = [f for f in relevant_fields if f in vals]

        if modified_relevant:
            _logger.info("   │  ⚠️ Se modificaron campos relevantes: %s", modified_relevant)
            _logger.info("   │     Se llamará a _update_calendar_event() para cada booking")

            for booking in self:
                if booking.calendar_event_id:
                    _logger.info("   │  → Booking ID %s tiene calendar.event ID %s - Actualizando...",
                               booking.id, booking.calendar_event_id.id)
                    booking._update_calendar_event()
                else:
                    _logger.info("   │  ℹ️ Booking ID %s NO tiene calendar.event asociado", booking.id)
        else:
            _logger.info("   │  ✓ No se modificaron campos relevantes - No se actualiza calendar.event")

        return res

    def unlink(self):
        """Override unlink to delete associated calendar.event."""
        # Guardar eventos para eliminarlos después
        events_to_delete = self.mapped('calendar_event_id')

        res = super().unlink()

        # Eliminar eventos asociados
        if events_to_delete:
            events_to_delete.sudo().unlink()

        return res

    def _create_calendar_event(self):
        """Create a calendar.event for this booking with WhatsApp alarms."""
        self.ensure_one()

        _logger.info("   ┌─ _create_calendar_event() INICIO para booking ID: %s", self.id)

        # Si ya tiene un calendar_event_id, no crear otro
        if self.calendar_event_id:
            _logger.info("   │  ⚠ Booking ID %s ya tiene un evento de calendario asociado (ID: %s)",
                        self.id, self.calendar_event_id.id)
            _logger.info("   └─ _create_calendar_event() FIN (ya existe)")
            return

        # Si ya tiene un meeting_id, usarlo en lugar de crear uno nuevo
        if hasattr(self, 'meeting_id') and self.meeting_id:
            _logger.info("   │  ℹ️ Booking ID %s ya tiene meeting_id (ID: %s) - Añadiendo alarmas WhatsApp",
                        self.id, self.meeting_id.id)

            whatsapp_alarms = self.env['calendar.alarm'].search([
                ('alarm_type', '=', 'whatsapp'),
                ('whatsapp_template_id', '!=', False)
            ])

            if whatsapp_alarms:
                self.meeting_id.with_context(
                    no_mail_to_attendees=True,
                    mail_notrack=True,
                ).sudo().write({
                    'alarm_ids': [(4, alarm.id) for alarm in whatsapp_alarms]
                })
                _logger.info("   │  ✓ Alarmas WhatsApp añadidas al meeting existente ID %s", self.meeting_id.id)

            self.calendar_event_id = self.meeting_id.id
            _logger.info("   └─ _create_calendar_event() FIN (meeting ya existía)")
            return

        _logger.info("   │  → Buscando template 'Recordatorio Cita Whatsapp' para calendar.event...")
        # Buscar el template de recordatorio por nombre
        reminder_template = self.env['mail.whatsapp.template'].search([
            ('name', '=', 'Recordatorio Cita Whatsapp'),  # Con mayúsculas y espacios
            ('model_id.model', '=', 'calendar.event')
        ], limit=1)

        if not reminder_template:
            _logger.warning("   │  ⚠ No se encontró el template 'Recordatorio Cita Whatsapp' para calendar.event")
        else:
            _logger.info("   │  ✓ Template 'Recordatorio Cita Whatsapp' encontrado (ID: %s)", reminder_template.id)

        _logger.info("   │  → Buscando alarmas WhatsApp configuradas...")
        # Buscar alarmas WhatsApp configuradas
        whatsapp_alarms = self.env['calendar.alarm'].search([
            ('alarm_type', '=', 'whatsapp'),
            ('whatsapp_template_id', '!=', False)
        ])

        if not whatsapp_alarms:
            _logger.warning("   │  ⚠ No hay alarmas WhatsApp configuradas. El evento se creará sin recordatorios WhatsApp.")
        else:
            _logger.info("   │  ✓ Encontradas %d alarmas WhatsApp para asignar al evento", len(whatsapp_alarms))
            for alarm in whatsapp_alarms:
                _logger.info("   │     - Alarma: %s (ID: %s, Template: %s)",
                           alarm.name, alarm.id, alarm.whatsapp_template_id.name if alarm.whatsapp_template_id else 'Sin template')

        try:
            _logger.info("   │  → Preparando valores para calendar.event...")
            _logger.info("   │     - name: %s", self.name)
            _logger.info("   │     - start: %s", self.start)
            _logger.info("   │     - stop: %s", self.stop)
            _logger.info("   │     - partner_ids: %s", self.partner_ids.ids if self.partner_ids else [])
            _logger.info("   │     - alarm_ids: %s", whatsapp_alarms.ids if whatsapp_alarms else [])

            event_vals = {
                'name': self.name or _('Reserva: %s') % self.display_name,
                'start': self.start,
                'stop': self.stop,
                'partner_ids': [(6, 0, self.partner_ids.ids)] if self.partner_ids else [],
                'alarm_ids': [(6, 0, whatsapp_alarms.ids)] if whatsapp_alarms else [],
                'description': _('Evento creado automáticamente desde reserva ID: %s') % self.id,
            }

            # Crear evento SIN enviar invitaciones por email
            _logger.info("   │  → Creando calendar.event con contexto:")
            _logger.info("   │     no_mail_to_attendees=True")
            _logger.info("   │     mail_create_nosubscribe=True")
            _logger.info("   │     mail_create_nolog=True")
            _logger.info("   │     mail_notrack=True")
            _logger.info("   │     tracking_disable=True")

            event = self.env['calendar.event'].with_context(
                no_mail_to_attendees=True,  # No enviar invitaciones a asistentes
                mail_create_nosubscribe=True,  # No suscribir automáticamente
                mail_create_nolog=True,  # No crear logs
                mail_notrack=True,  # No tracking
                tracking_disable=True,  # Desactivar tracking completamente
                # Contexto adicional para bloquear completamente los emails
                mail_create_nothread=True,
                mail_auto_delete=True,
            ).sudo().create(event_vals)
            self.calendar_event_id = event.id

            _logger.info("   │  ✓ Evento de calendario creado: ID %s", event.id)
            _logger.info("   │     - Start: %s", event.start)
            _logger.info("   │     - Stop: %s", event.stop)
            _logger.info("   │     - Attendees: %s", len(event.attendee_ids))
            _logger.info("   │     - Alarms: %s", len(event.alarm_ids))

            _logger.info("   │")
            _logger.info("   │  📊 RESUMEN:")
            _logger.info("   │     Evento de calendario ID %s creado para booking ID %s con %d alarmas WhatsApp",
                        event.id, self.id, len(whatsapp_alarms))
            _logger.info("   └─ _create_calendar_event() FIN")

        except Exception as e:
            _logger.error("   │  ❌ ERROR al crear evento de calendario para booking ID %s: %s",
                        self.id, str(e), exc_info=True)
            _logger.info("   └─ _create_calendar_event() FIN (con error)")

    def _update_calendar_event(self):
        """Update the associated calendar.event when booking changes."""
        self.ensure_one()

        if not self.calendar_event_id:
            return

        try:
            _logger.info("   │  → Actualizando calendar.event ID %s desde booking ID %s",
                        self.calendar_event_id.id, self.id)

            event_vals = {
                'name': self.name or _('Reserva: %s') % self.display_name,
                'start': self.start,
                'stop': self.stop,
                'partner_ids': [(6, 0, self.partner_ids.ids)] if self.partner_ids else [],
            }

            _logger.info("   │     Nuevos valores: start=%s, stop=%s", event_vals['start'], event_vals['stop'])
            _logger.info("   │     Usando contexto: no_mail_to_attendees=True (para evitar emails)")

            # Actualizar CON contexto para evitar emails
            self.calendar_event_id.with_context(
                no_mail_to_attendees=True,
                mail_notrack=True,
                mail_create_nolog=True,
                tracking_disable=True,
            ).sudo().write(event_vals)

            _logger.info("   │  ✓ Evento de calendario ID %s actualizado desde booking ID %s",
                        self.calendar_event_id.id, self.id)

        except Exception as e:
            _logger.error("   │  ❌ Error al actualizar evento de calendario para booking ID %s: %s",
                        self.id, str(e), exc_info=True)

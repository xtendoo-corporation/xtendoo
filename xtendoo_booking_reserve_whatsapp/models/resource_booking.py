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
        bookings = super().create(vals_list)

        for booking in bookings:
            # Crear evento de calendario con alarmas
            booking._create_calendar_event()

        return bookings

    def write(self, vals):
        """Override write to update calendar.event if booking changes."""
        res = super().write(vals)

        # Si se modificaron campos relevantes, actualizar el evento
        relevant_fields = ['start', 'stop', 'name', 'partner_ids']
        if any(field in vals for field in relevant_fields):
            for booking in self:
                if booking.calendar_event_id:
                    booking._update_calendar_event()

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

        if self.calendar_event_id:
            _logger.info("Booking ID %s ya tiene un evento de calendario asociado (ID: %s)",
                        self.id, self.calendar_event_id.id)
            return

        # Buscar alarmas WhatsApp por defecto
        # Buscar el template de recordatorio por nombre
        reminder_template = self.env['mail.whatsapp.template'].search([
            ('name', '=', 'recordatorio_cita_whatsapp'),
            ('model_id.model', '=', 'calendar.event')
        ], limit=1)

        if not reminder_template:
            _logger.warning("No se encontró el template 'recordatorio_cita_whatsapp' para calendar.event")
        else:
            _logger.info("Template 'recordatorio_cita_whatsapp' encontrado (ID: %s)", reminder_template.id)

        # Buscar alarmas WhatsApp configuradas
        whatsapp_alarms = self.env['calendar.alarm'].search([
            ('alarm_type', '=', 'whatsapp'),
            ('whatsapp_template_id', '!=', False)
        ])

        if not whatsapp_alarms:
            _logger.warning("No hay alarmas WhatsApp configuradas. El evento se creará sin recordatorios WhatsApp.")
        else:
            _logger.info("Encontradas %d alarmas WhatsApp para asignar al evento", len(whatsapp_alarms))

        try:
            event_vals = {
                'name': self.name or _('Reserva: %s') % self.display_name,
                'start': self.start,
                'stop': self.stop,
                'partner_ids': [(6, 0, self.partner_ids.ids)] if self.partner_ids else [],
                'alarm_ids': [(6, 0, whatsapp_alarms.ids)] if whatsapp_alarms else [],
                'description': _('Evento creado automáticamente desde reserva ID: %s') % self.id,
            }

            # Crear evento SIN enviar invitaciones por email
            event = self.env['calendar.event'].with_context(
                no_mail_to_attendees=True,  # No enviar invitaciones a asistentes
                mail_create_nosubscribe=True,  # No suscribir automáticamente
                mail_create_nolog=True,  # No crear logs
                mail_notrack=True,  # No tracking
            ).sudo().create(event_vals)
            self.calendar_event_id = event.id

            _logger.info(
                "Evento de calendario ID %s creado para booking ID %s con %d alarmas WhatsApp",
                event.id, self.id, len(whatsapp_alarms)
            )

        except Exception as e:
            _logger.error(
                "Error al crear evento de calendario para booking ID %s: %s",
                self.id, str(e), exc_info=True
            )

    def _update_calendar_event(self):
        """Update the associated calendar.event when booking changes."""
        self.ensure_one()

        if not self.calendar_event_id:
            return

        try:
            event_vals = {
                'name': self.name or _('Reserva: %s') % self.display_name,
                'start': self.start,
                'stop': self.stop,
                'partner_ids': [(6, 0, self.partner_ids.ids)] if self.partner_ids else [],
            }

            self.calendar_event_id.sudo().write(event_vals)

            _logger.info(
                "Evento de calendario ID %s actualizado desde booking ID %s",
                self.calendar_event_id.id, self.id
            )

        except Exception as e:
            _logger.error(
                "Error al actualizar evento de calendario para booking ID %s: %s",
                self.id, str(e), exc_info=True
            )

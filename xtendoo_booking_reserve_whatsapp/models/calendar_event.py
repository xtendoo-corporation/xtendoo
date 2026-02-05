# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # Campos computados para formatear fecha/hora para WhatsApp
    start_time = fields.Char(
        string='Start Time',
        compute='_compute_formatted_times',
        store=True,  # Almacenado para que aparezca en selector de variables
        help="Hora de inicio formateada (HH:MM)"
    )

    stop_time = fields.Char(
        string='Stop Time',
        compute='_compute_formatted_times',
        store=True,  # Almacenado para que aparezca en selector de variables
        help="Hora de fin formateada (HH:MM)"
    )

    formatted_start_date = fields.Char(
        string='Formatted Start Date',
        compute='_compute_formatted_times',
        store=True,  # Almacenado para que aparezca en selector de variables
        help="Fecha de inicio formateada (DD/MM/YYYY)"
    )

    formatted_stop_date = fields.Char(
        string='Formatted Stop Date',
        compute='_compute_formatted_times',
        store=True,  # Almacenado para que aparezca en selector de variables
        help="Fecha de fin formateada (DD/MM/YYYY)"
    )

    @api.depends('start', 'stop', 'start_date', 'stop_date')
    def _compute_formatted_times(self):
        """Compute formatted date/time strings for WhatsApp messages."""
        for event in self:
            # Formatear hora de inicio
            if event.start:
                event.start_time = event.start.strftime('%H:%M')
                event.formatted_start_date = event.start.strftime('%d/%m/%Y')
            else:
                event.start_time = ''
                event.formatted_start_date = ''

            # Formatear hora de fin
            if event.stop:
                event.stop_time = event.stop.strftime('%H:%M')
                event.formatted_stop_date = event.stop.strftime('%d/%m/%Y')
            else:
                event.stop_time = ''
                event.formatted_stop_date = ''

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to prevent sending emails for auto-created events from bookings."""
        _logger.info("   │     📅 calendar.event.create() llamado")
        _logger.info("   │        Cantidad de eventos a crear: %d", len(vals_list))
        _logger.info("   │        Contexto: no_mail_to_attendees=%s", self.env.context.get('no_mail_to_attendees'))

        # Si el contexto indica que no se deben enviar emails, desactivar notificaciones
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 BLOQUEANDO envío de emails en calendar.event.create()")
            # Desactivar completamente el envío de notificaciones
            result = super(CalendarEvent, self.with_context(
                mail_notrack=True,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                tracking_disable=True,
                # Contexto específico de calendar para desactivar invitaciones
                no_mail_to_attendees=True,
            )).create(vals_list)
            _logger.info("   │     ✓ Eventos creados SIN enviar emails: IDs %s", result.ids)
            return result

        _logger.info("   │     ⚠️ NO se bloqueará el envío de emails (contexto no establecido)")
        return super().create(vals_list)

    def write(self, vals):
        """Override write to prevent sending emails for auto-created events from bookings."""
        _logger.info("   │     📅 calendar.event.write() llamado para eventos IDs: %s", self.ids)
        _logger.info("   │        Campos a modificar: %s", list(vals.keys()))
        _logger.info("   │        Contexto: no_mail_to_attendees=%s", self.env.context.get('no_mail_to_attendees'))

        # Si el contexto indica que no se deben enviar emails, desactivar notificaciones
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 BLOQUEANDO envío de emails en calendar.event.write()")
            result = super(CalendarEvent, self.with_context(
                mail_notrack=True,
                mail_create_nolog=True,
                tracking_disable=True,
                no_mail_to_attendees=True,
                # Contexto adicional para bloquear completamente
                mail_auto_delete=True,
            )).write(vals)
            _logger.info("   │     ✓ Eventos actualizados SIN enviar emails")
            return result

        _logger.info("   │     ⚠️ NO se bloqueará el envío de emails (contexto no establecido)")
        return super().write(vals)

    def _get_attendees_to_notify(self):
        """Override to prevent sending emails when context flag is set."""
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 Bloqueando _get_attendees_to_notify()")
            return self.env['calendar.attendee']

        return super()._get_attendees_to_notify()

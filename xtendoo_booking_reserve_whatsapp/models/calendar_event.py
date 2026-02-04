# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

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

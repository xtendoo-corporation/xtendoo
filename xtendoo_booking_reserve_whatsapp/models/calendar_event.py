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
        # Si el contexto indica que no se deben enviar emails, desactivar notificaciones
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 Desactivando envío de emails en calendar.event.create()")
            # Desactivar completamente el envío de notificaciones
            return super(CalendarEvent, self.with_context(
                mail_notrack=True,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                tracking_disable=True,
                # Contexto específico de calendar para desactivar invitaciones
                no_mail_to_attendees=True,
            )).create(vals_list)

        return super().create(vals_list)

    def write(self, vals):
        """Override write to prevent sending emails for auto-created events from bookings."""
        # Si el contexto indica que no se deben enviar emails, desactivar notificaciones
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 Desactivando envío de emails en calendar.event.write()")
            return super(CalendarEvent, self.with_context(
                mail_notrack=True,
                mail_create_nolog=True,
                tracking_disable=True,
                no_mail_to_attendees=True,
            )).write(vals)

        return super().write(vals)

    def _get_attendees_to_notify(self):
        """Override to prevent sending emails when context flag is set."""
        if self.env.context.get('no_mail_to_attendees'):
            _logger.info("   │     🔒 Bloqueando _get_attendees_to_notify()")
            return self.env['calendar.attendee']

        return super()._get_attendees_to_notify()

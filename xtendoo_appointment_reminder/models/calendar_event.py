from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # Campos para seguimiento de recordatorios WhatsApp
    whatsapp_reminder_sent = fields.Boolean(
        string='Recordatorio WhatsApp Enviado',
        default=False,
        help="Indica si se ha enviado el recordatorio por WhatsApp"
    )

    whatsapp_reminder_date = fields.Datetime(
        string='Fecha Envío WhatsApp',
        help="Fecha y hora en que se envió el recordatorio por WhatsApp"
    )

    whatsapp_reminder_count = fields.Integer(
        string='Recordatorios WhatsApp',
        default=0,
        help="Número de recordatorios WhatsApp enviados"
    )

    # Campo computado para obtener el número móvil del partner principal
    mobile = fields.Char(
        string='Mobile',
        compute='_compute_mobile',
        store=False,
        help="Número móvil del partner principal del evento"
    )

    # Campo computado para obtener el número de teléfono del partner principal
    phone = fields.Char(
        string='Phone',
        compute='_compute_phone',
        store=False,
        help="Número de teléfono del partner principal del evento"
    )

    @api.depends('partner_ids', 'attendee_ids')
    def _compute_mobile(self):
        """Computa el número móvil del partner principal o asistente"""
        for event in self:
            mobile = False

            # Buscar en los asistentes del evento
            for attendee in event.attendee_ids:
                if attendee.partner_id and attendee.partner_id.mobile:
                    mobile = attendee.partner_id.mobile
                    break

            # Si no se encontró en asistentes, buscar en partners del evento
            if not mobile and event.partner_ids:
                for partner in event.partner_ids:
                    if partner.mobile:
                        mobile = partner.mobile
                        break

            event.mobile = mobile

    @api.depends('partner_ids', 'attendee_ids')
    def _compute_phone(self):
        """Computa el número de teléfono del partner principal o asistente"""
        for event in self:
            phone = False

            # Buscar en los asistentes del evento
            for attendee in event.attendee_ids:
                if attendee.partner_id and attendee.partner_id.phone:
                    phone = attendee.partner_id.phone
                    break

            # Si no se encontró en asistentes, buscar en partners del evento
            if not phone and event.partner_ids:
                for partner in event.partner_ids:
                    if partner.phone:
                        phone = partner.phone
                        break

            event.phone = phone

    @api.model
    def process_whatsapp_reminders(self):
        """
        Método llamado por el cron para procesar recordatorios WhatsApp pendientes
        """
        # Buscar eventos próximos que tengan recordatorios WhatsApp configurados
        events_to_process = self.search([
            ('start', '>', fields.Datetime.now()),
            ('alarm_ids.alarm_type', '=', 'whatsapp'),
            ('whatsapp_reminder_sent', '=', False)
        ])

        for event in events_to_process:
            try:
                event._process_whatsapp_reminders()
            except Exception as e:
                _logger.error(f"Error procesando recordatorios para evento {event.id}: {e}")

    def _process_whatsapp_reminders(self):
        """
        Procesa los recordatorios WhatsApp para este evento específico
        """
        current_time = fields.Datetime.now()

        # Obtener recordatorios WhatsApp configurados para este evento
        whatsapp_alarms = self.alarm_ids.filtered(lambda a: a.alarm_type == 'whatsapp')

        for alarm in whatsapp_alarms:
            # Calcular cuándo se debe enviar el recordatorio
            reminder_time = self.start - fields.Datetime.to_datetime(
                f"1970-01-01 {alarm.duration_minutes//60:02d}:{alarm.duration_minutes%60:02d}:00"
            )

            # Si es tiempo de enviar el recordatorio
            if current_time >= reminder_time and not self.whatsapp_reminder_sent:
                try:
                    success = alarm._send_whatsapp_reminder(self)
                    if success:
                        self.whatsapp_reminder_count += 1
                        _logger.info(f"Recordatorio WhatsApp enviado para evento {self.name}")
                    else:
                        _logger.warning(f"Fallo al enviar recordatorio WhatsApp para evento {self.name}")
                except Exception as e:
                    _logger.error(f"Error enviando recordatorio WhatsApp: {e}")

    def action_send_whatsapp_reminder(self):
        """
        Acción manual para enviar recordatorio WhatsApp
        """
        whatsapp_alarms = self.alarm_ids.filtered(lambda a: a.alarm_type == 'whatsapp')

        if not whatsapp_alarms:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Sin Recordatorios"),
                    'message': _("No hay recordatorios WhatsApp configurados para este evento"),
                    'type': 'warning'
                }
            }

        success_count = 0
        for alarm in whatsapp_alarms:
            try:
                if alarm._send_whatsapp_reminder(self):
                    success_count += 1
            except Exception as e:
                _logger.error(f"Error enviando recordatorio manual: {e}")

        if success_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("WhatsApp Enviado"),
                    'message': _("Se enviaron %s recordatorio(s) por WhatsApp") % success_count,
                    'type': 'success'
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("No se pudo enviar ningún recordatorio por WhatsApp"),
                    'type': 'warning'
                }
            }

    def get_whatsapp_reminder_context(self):
        """
        Obtiene el contexto para las plantillas de WhatsApp
        """
        return {
            'event_name': self.name,
            'start_date': self.start.strftime('%d/%m/%Y') if self.start else '',
            'start_time': self.start.strftime('%H:%M') if self.start else '',
            'location': self.location or '',
            'description': self.description or '',
            'organizer': self.user_id.name if self.user_id else '',
            'attendee_name': self.partner_id.name if self.partner_id else '',
            'company_name': self.env.company.name,
        }

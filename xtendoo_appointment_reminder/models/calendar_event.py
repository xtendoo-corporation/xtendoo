from odoo import models, fields, api, _
import logging
import pytz

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

    start_local = fields.Char(string='Hora local', compute='_compute_start_local')

    @api.depends('start')
    def _compute_start_local(self):
        tz = pytz.timezone(self.env.user.tz or 'Europe/Madrid')
        for event in self:
            if event.start:
                event.start_local = event.start.astimezone(tz).strftime('%d/%m/%Y %H:%M')
            else:
                event.start_local = ''

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
        try:
            # Verificar que el módulo WhatsApp esté instalado
            if not self.env['ir.module.module'].search([('name', '=', 'whatsapp'), ('state', '=', 'installed')]):
                _logger.warning("El módulo WhatsApp no está instalado")
                return

            # Hora actual para comparaciones
            current_time = fields.Datetime.now()

            # Buscar TODOS los eventos futuros que tengan recordatorios WhatsApp configurados
            # y no se hayan enviado aún, en lugar de filtrar por tiempo aquí
            events_to_process = self.search([
                ('start', '!=', False),  # Eventos con fecha de inicio
                ('alarm_ids.alarm_type', '=', 'whatsapp'),  # Con alarma tipo whatsapp
                ('whatsapp_reminder_sent', '=', False)  # Que no se haya enviado recordatorio
            ])

            if not events_to_process:
                _logger.info("No se encontraron eventos pendientes para recordatorios WhatsApp")
                # Verificar si existen eventos futuros en general para diagnosticar
                future_events = self.search_count([('start', '>', current_time)])
                events_with_alarms = self.search_count([
                    ('start', '>', current_time),
                    ('alarm_ids.alarm_type', '=', 'whatsapp')
                ])
                _logger.info(f"Diagnóstico: Existen {future_events} eventos futuros, {events_with_alarms} con alarmas WhatsApp")
                return

            _logger.info(f"Procesando {len(events_to_process)} eventos para recordatorios WhatsApp")

            # Verificar cada evento para ver si ya es hora de enviar el recordatorio
            reminder_count = 0
            for event in events_to_process:
                try:
                    # Solo procesar eventos que aún no han pasado
                    if event.start <= current_time:
                        _logger.debug(f"Saltando evento {event.name} (ID: {event.id}) porque ya ha pasado")
                        continue

                    # Verificar alarmas de WhatsApp para este evento
                    for alarm in event.alarm_ids.filtered(lambda a: a.alarm_type == 'whatsapp'):
                        # Calcular cuándo se debe enviar el recordatorio
                        from datetime import timedelta
                        reminder_delta = timedelta(minutes=alarm.duration_minutes)
                        reminder_time = event.start - reminder_delta

                        # Si ya es tiempo de enviar el recordatorio
                        if current_time >= reminder_time:
                            _logger.info(f"Enviando recordatorio para evento {event.name} (ID: {event.id}) - Fecha evento: {event.start}, hora recordatorio: {reminder_time}")
                            success = alarm._send_whatsapp_reminder(event)
                            if success:
                                event.write({
                                    'whatsapp_reminder_sent': True,
                                    'whatsapp_reminder_date': fields.Datetime.now(),
                                    'whatsapp_reminder_count': event.whatsapp_reminder_count + 1
                                })
                                reminder_count += 1
                                _logger.info(f"Recordatorio WhatsApp enviado para evento {event.name}")
                            else:
                                _logger.warning(f"Fallo al enviar recordatorio WhatsApp para evento {event.name}")
                        else:
                            _logger.info(f"Aún no es tiempo de enviar recordatorio para evento {event.name} (ID: {event.id}). Programado para: {reminder_time}, hora actual: {current_time}")
                except Exception as e:
                    _logger.error(f"Error procesando recordatorios para evento {event.id}: {e}", exc_info=True)

            _logger.info(f"Proceso finalizado. Se enviaron {reminder_count} recordatorios de WhatsApp")

        except Exception as e:
            _logger.error(f"Error general en process_whatsapp_reminders: {e}", exc_info=True)

    def _process_whatsapp_reminders(self):
        """
        Procesa los recordatorios WhatsApp para este evento específico
        """
        current_time = fields.Datetime.now()

        # Obtener recordatorios WhatsApp configurados para este evento
        whatsapp_alarms = self.alarm_ids.filtered(lambda a: a.alarm_type == 'whatsapp')

        for alarm in whatsapp_alarms:
            # Calcular cuándo se debe enviar el recordatorio
            from datetime import timedelta
            reminder_delta = timedelta(minutes=alarm.duration_minutes)
            reminder_time = self.start - reminder_delta

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
        try:
            # Verificar que el módulo WhatsApp esté instalado
            if not self.env['ir.module.module'].search([('name', '=', 'whatsapp'), ('state', '=', 'installed')]):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Módulo No Disponible"),
                        'message': _("El módulo WhatsApp no está instalado"),
                        'type': 'warning'
                    }
                }

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

            # Verificar que hay una cuenta de WhatsApp activa
            whatsapp_account = self.env['whatsapp.account'].search([
                ('active', '=', True)
            ], limit=1)

            # Si no hay cuentas con campo 'active', buscar cualquier cuenta disponible
            if not whatsapp_account:
                whatsapp_account = self.env['whatsapp.account'].search([], limit=1)

            if not whatsapp_account:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Sin Cuenta WhatsApp"),
                        'message': _("No hay cuenta de WhatsApp activa configurada"),
                        'type': 'warning'
                    }
                }

            # Verificar que el evento tiene un contacto con teléfono
            partner = self._get_event_partner()
            if not partner:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Sin Contacto"),
                        'message': _("No se encontró contacto para este evento"),
                        'type': 'warning'
                    }
                }

            if not partner.mobile and not partner.phone:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Sin Teléfono"),
                        'message': _("El contacto %s no tiene número de teléfono") % partner.name,
                        'type': 'warning'
                    }
                }

            success_count = 0
            error_messages = []

            for alarm in whatsapp_alarms:
                try:
                    if alarm._send_whatsapp_reminder(self):
                        success_count += 1
                    else:
                        error_messages.append(f"Error con recordatorio: {alarm.name}")
                except Exception as e:
                    _logger.error(f"Error enviando recordatorio manual: {e}")
                    error_messages.append(f"Error con recordatorio: {alarm.name} - {str(e)}")

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
                error_msg = "\n".join(error_messages) if error_messages else "Error desconocido"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Error"),
                        'message': _("No se pudo enviar ningún recordatorio por WhatsApp:\n%s") % error_msg,
                        'type': 'danger'
                    }
                }

        except Exception as e:
            _logger.error(f"Error en action_send_whatsapp_reminder: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("Error inesperado: %s") % str(e),
                    'type': 'danger'
                }
            }

    def _get_event_partner(self):
        """
        Obtiene el partner principal del evento
        """
        # Buscar en los asistentes del evento
        for attendee in self.attendee_ids:
            if attendee.partner_id:
                return attendee.partner_id

        # Si no hay asistentes, buscar en el partner del evento
        if self.partner_ids:
            return self.partner_ids[0]

        return False

    def get_whatsapp_reminder_context(self):
        """
        Obtiene el contexto para las plantillas de WhatsApp
        """
        partner = self._get_event_partner()
        return {
            'event_name': self.name or '',
            'start_date': self.start.strftime('%d/%m/%Y') if self.start else '',
            'start_time': self.start.strftime('%H:%M') if self.start else '',
            'location': self.location or '',
            'description': self.description or '',
            'organizer': self.user_id.name if self.user_id else '',
            'attendee_name': partner.name if partner else '',
            'company_name': self.env.company.name,
        }

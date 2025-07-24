from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CalendarAlarm(models.Model):
    _inherit = 'calendar.alarm'

    alarm_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp')],
        ondelete={'whatsapp': 'set default'}
    )

    whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='WhatsApp Template',
        domain=[('model', '=', 'calendar.event')],
        help="Template de WhatsApp para el recordatorio"
    )

    @api.onchange('alarm_type')
    def _onchange_alarm_type_whatsapp(self):
        """Limpiar el template de WhatsApp si no es tipo WhatsApp"""
        if self.alarm_type != 'whatsapp':
            self.whatsapp_template_id = False

    def _send_whatsapp_reminder(self, calendar_event):
        """
        Envía recordatorio de evento por WhatsApp
        """
        try:
            # Verificar que hay una cuenta de WhatsApp activa
            whatsapp_account = self.env['whatsapp.account'].search([
                ('active', '=', True)
            ], limit=1)

            if not whatsapp_account:
                _logger.error("No se encontró cuenta de WhatsApp activa para recordatorios")
                return False

            # Obtener el número de teléfono del participante
            attendee_phone = self._get_attendee_phone(calendar_event)
            if not attendee_phone:
                _logger.warning(f"No se encontró teléfono para el evento {calendar_event.name}")
                return False

            # Preparar el mensaje del recordatorio
            message = self._prepare_whatsapp_message(calendar_event)

            # Enviar mensaje de WhatsApp
            success = self._send_whatsapp_message(
                whatsapp_account,
                attendee_phone,
                message,
                calendar_event
            )

            if success:
                _logger.info(f"Recordatorio WhatsApp enviado para evento {calendar_event.name}")
                # Marcar como enviado en el evento
                calendar_event.write({
                    'whatsapp_reminder_sent': True,
                    'whatsapp_reminder_date': fields.Datetime.now()
                })

            return success

        except Exception as e:
            _logger.error(f"Error enviando recordatorio WhatsApp: {e}")
            return False

    def _get_attendee_phone(self, calendar_event):
        """
        Obtiene el número de teléfono del asistente principal
        """
        # Buscar en los asistentes del evento
        for attendee in calendar_event.attendee_ids:
            if attendee.partner_id and attendee.partner_id.mobile:
                return self._normalize_phone_number(attendee.partner_id.mobile)
            elif attendee.partner_id and attendee.partner_id.phone:
                return self._normalize_phone_number(attendee.partner_id.phone)

        # Si no hay asistentes, buscar en el partner del evento
        if calendar_event.partner_ids:
            for partner in calendar_event.partner_ids:
                if partner.mobile:
                    return self._normalize_phone_number(partner.mobile)
                elif partner.phone:
                    return self._normalize_phone_number(partner.phone)

        return False

    def _normalize_phone_number(self, phone):
        """
        Normaliza el número de teléfono eliminando espacios y caracteres especiales
        """
        if not phone:
            return False

        import re
        # Eliminar espacios, guiones y paréntesis
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)

        # Si no empieza con +, asumir código de país (España por defecto)
        if not clean_phone.startswith('+'):
            if len(clean_phone) == 9:  # Número español sin código
                clean_phone = '+34' + clean_phone

        return clean_phone

    def _prepare_whatsapp_message(self, calendar_event):
        """
        Prepara el mensaje de recordatorio para WhatsApp
        """
        if self.whatsapp_template_id:
            # Usar plantilla personalizada
            return self.whatsapp_template_id._render_template(calendar_event.id)
        else:
            # Mensaje predeterminado
            return self._get_default_whatsapp_message(calendar_event)

    def _get_default_whatsapp_message(self, calendar_event):
        """
        Genera un mensaje predeterminado para el recordatorio
        """
        import pytz
        from datetime import datetime

        # Obtener zona horaria
        user_tz = self.env.user.tz or 'Europe/Madrid'
        local_tz = pytz.timezone(user_tz)

        # Formatear fecha y hora en zona local
        if calendar_event.start:
            utc_time = calendar_event.start.replace(tzinfo=pytz.UTC)
            local_time = utc_time.astimezone(local_tz)
            date_str = local_time.strftime('%d/%m/%Y')
            time_str = local_time.strftime('%H:%M')
        else:
            date_str = "fecha por confirmar"
            time_str = "hora por confirmar"

        # Información de ubicación
        location = calendar_event.location or "ubicación por confirmar"

        # Nombre del cliente
        client_name = "Estimado cliente"
        if calendar_event.partner_ids:
            client_name = calendar_event.partner_ids[0].name
        elif calendar_event.attendee_ids:
            client_name = calendar_event.attendee_ids[0].partner_id.name or calendar_event.attendee_ids[0].display_name

        message = f"""📅 *Recordatorio de Evento*

Hola {client_name},

Te recordamos tu evento programado:

📋 *Asunto:* {calendar_event.name}
📅 *Fecha:* {date_str}
🕐 *Hora:* {time_str}
📍 *Ubicación:* {location}

Si necesitas cancelar o reprogramar, por favor contáctanos con anticipación.

¡Te esperamos!

{self.env.company.name}"""

        return message

    def _send_whatsapp_message(self, whatsapp_account, phone_number, message, calendar_event):
        """
        Envía el mensaje de WhatsApp usando la API
        """
        try:
            import requests

            # Obtener token de acceso
            access_token = self._get_whatsapp_token(whatsapp_account)
            if not access_token:
                return False

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{whatsapp_account.phone_uid}/messages"

            # Headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Limpiar número de teléfono
            clean_phone = phone_number.lstrip('+')

            # Datos del mensaje
            data = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }

            _logger.info(f"Enviando recordatorio WhatsApp a {clean_phone} para evento {calendar_event.name}")

            # Realizar petición
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                _logger.info(f"Recordatorio WhatsApp enviado exitosamente")
                return True
            else:
                _logger.error(f"Error en API WhatsApp: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error enviando mensaje WhatsApp: {e}")
            return False

    def _get_whatsapp_token(self, whatsapp_account):
        """
        Obtiene el token de acceso de la cuenta de WhatsApp
        """
        token_fields = ['access_token', 'token', 'app_secret', 'permanent_access_token']

        for field in token_fields:
            if hasattr(whatsapp_account, field):
                token_value = getattr(whatsapp_account, field)
                if token_value:
                    return token_value

        _logger.error("No se encontró token de acceso en la cuenta de WhatsApp")
        return False


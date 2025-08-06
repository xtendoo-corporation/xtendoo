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
        Envía recordatorio de evento por WhatsApp usando el módulo nativo de Odoo 18
        """
        try:
            # Verificar que existe el módulo whatsapp y está instalado
            if not self.env['ir.module.module'].search([('name', '=', 'whatsapp'), ('state', '=', 'installed')]):
                _logger.error("El módulo WhatsApp no está instalado")
                return False

            # Obtener la cuenta de WhatsApp activa
            WhatsAppAccount = self.env['whatsapp.account']
            whatsapp_account = WhatsAppAccount.search([
                ('status', '=', 'active')
            ], limit=1)

            if not whatsapp_account:
                _logger.error("No se encontró cuenta de WhatsApp activa")
                return False

            # Obtener el número de teléfono del participante
            attendee_phone = self._get_attendee_phone(calendar_event)
            if not attendee_phone:
                _logger.warning(f"No se encontró teléfono para el evento {calendar_event.name}")
                return False

            # Obtener o crear el contacto en WhatsApp
            partner = self._get_event_partner(calendar_event)
            if not partner:
                _logger.warning(f"No se encontró partner para el evento {calendar_event.name}")
                return False

            # Usar el servicio nativo de WhatsApp de Odoo 18
            success = self._send_via_odoo_whatsapp(whatsapp_account, partner, calendar_event)

            if success:
                _logger.info(f"Recordatorio WhatsApp enviado para evento {calendar_event.name}")
                # Marcar como enviado en el evento
                calendar_event.write({
                    'whatsapp_reminder_sent': True,
                    'whatsapp_reminder_date': fields.Datetime.now()
                })

            return success

        except Exception as e:
            _logger.error(f"Error enviando recordatorio WhatsApp: {e}", exc_info=True)
            return False

    def _send_via_odoo_whatsapp(self, whatsapp_account, partner, calendar_event):
        """
        Envía mensaje usando el sistema nativo de WhatsApp de Odoo 18
        """
        try:
            # Preparar el mensaje
            message_body = self._prepare_whatsapp_message(calendar_event)

            # Crear el mensaje de WhatsApp usando el modelo nativo
            WhatsAppMessage = self.env['whatsapp.message']

            # Verificar si el partner tiene un número de WhatsApp válido
            if not partner.mobile and not partner.phone:
                _logger.error(f"Partner {partner.name} no tiene número de teléfono")
                return False

            phone_number = partner.mobile or partner.phone
            normalized_phone = self._normalize_phone_number(phone_number)

            if not normalized_phone:
                _logger.error(f"No se pudo normalizar el número de teléfono: {phone_number}")
                return False

            # Crear el mensaje de WhatsApp
            message_vals = {
                'body': message_body,
                'wa_account_id': whatsapp_account.id,
                'mobile_number': normalized_phone,
                'mobile_number_formatted': normalized_phone,
                'message_type': 'outbound',
                'state': 'outgoing',
            }

            # Si hay plantilla, usarla
            if self.whatsapp_template_id:
                message_vals.update({
                    'wa_template_id': self.whatsapp_template_id.id,
                    'template_params': self._get_template_params(calendar_event),
                })

            whatsapp_message = WhatsAppMessage.create(message_vals)

            # Enviar el mensaje
            try:
                whatsapp_message.send()

                # Verificar si se envió correctamente
                if whatsapp_message.state == 'sent':
                    return True
                else:
                    _logger.error(f"El mensaje no se envió correctamente. Estado: {whatsapp_message.state}")
                    return False

            except Exception as send_error:
                _logger.error(f"Error al enviar mensaje WhatsApp: {send_error}")
                return False

        except Exception as e:
            _logger.error(f"Error en _send_via_odoo_whatsapp: {e}", exc_info=True)
            return False

    def _get_event_partner(self, calendar_event):
        """
        Obtiene el partner principal del evento
        """
        # Buscar en los asistentes del evento
        for attendee in calendar_event.attendee_ids:
            if attendee.partner_id:
                return attendee.partner_id

        # Si no hay asistentes, buscar en el partner del evento
        if calendar_event.partner_ids:
            return calendar_event.partner_ids[0]

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

    def _prepare_whatsapp_message(self, calendar_event):
        """
        Prepara el mensaje de recordatorio para WhatsApp
        """
        if self.whatsapp_template_id:
            # Usar plantilla personalizada
            try:
                # Para Odoo 18, usar el método correcto de renderizado
                template_params = self._get_template_params(calendar_event)
                return self.whatsapp_template_id._render_template([calendar_event.id], template_params)[calendar_event.id]
            except Exception as e:
                _logger.warning(f"Error renderizando plantilla, usando mensaje por defecto: {e}")
                return self._get_default_whatsapp_message(calendar_event)
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
        partner = self._get_event_partner(calendar_event)
        if partner:
            client_name = partner.name

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

    def _normalize_phone_number(self, phone):
        """
        Normaliza el número de teléfono para WhatsApp
        """
        if not phone:
            return False

        import re
        # Eliminar espacios, guiones, paréntesis y puntos
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)

        # Eliminar caracteres no numéricos excepto el +
        clean_phone = re.sub(r'[^\d\+]', '', clean_phone)

        # Si no empieza con +, asumir código de país España
        if not clean_phone.startswith('+'):
            if len(clean_phone) == 9:  # Número español sin código
                clean_phone = '+34' + clean_phone
            elif len(clean_phone) == 11 and clean_phone.startswith('34'):
                clean_phone = '+' + clean_phone
            else:
                # Para otros casos, añadir +34 por defecto
                clean_phone = '+34' + clean_phone

        # Validar formato básico
        if len(clean_phone) < 10:
            _logger.warning(f"Número de teléfono demasiado corto: {clean_phone}")
            return False

        return clean_phone

    def _get_template_params(self, calendar_event):
        """
        Obtiene los parámetros para la plantilla de WhatsApp
        """
        import pytz

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

        return {
            'event_name': calendar_event.name or '',
            'start_date': date_str,
            'start_time': time_str,
            'location': calendar_event.location or 'Por confirmar',
            'description': calendar_event.description or '',
            'company_name': self.env.company.name or '',
            'client_name': self._get_event_partner(calendar_event).name if self._get_event_partner(calendar_event) else 'Estimado cliente'
        }

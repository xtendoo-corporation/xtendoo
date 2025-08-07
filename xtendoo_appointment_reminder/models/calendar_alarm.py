from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import re

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
            whatsapp_account = self._get_whatsapp_account()
            if not whatsapp_account:
                _logger.error("No se encontró cuenta de WhatsApp disponible")
                return False

            # Obtener el partner del evento
            partner = self._get_event_partner(calendar_event)
            if not partner:
                _logger.warning(f"No se encontró partner para el evento {calendar_event.name}")
                return False

            # Obtener el número de teléfono
            phone_number = self._get_partner_phone(partner)
            if not phone_number:
                _logger.warning(f"No se encontró teléfono para el partner {partner.name}")
                return False

            # Enviar el mensaje
            success = self._send_whatsapp_message_odoo18(whatsapp_account, partner, calendar_event)

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

    def _get_whatsapp_account(self):
        """Obtiene una cuenta de WhatsApp disponible"""
        WhatsAppAccount = self.env['whatsapp.account']

        # Buscar cuenta activa
        account = WhatsAppAccount.search([('active', '=', True)], limit=1)

        # Si no hay cuenta activa, buscar cualquier cuenta
        if not account:
            account = WhatsAppAccount.search([], limit=1)

        return account

    def _send_whatsapp_message_odoo18(self, whatsapp_account, partner, calendar_event):
        """
        Envía mensaje usando la API de WhatsApp de Odoo 18
        """
        try:
            # Preparar el mensaje
            message_body = self._prepare_whatsapp_message(calendar_event)
            phone_number = self._get_partner_phone(partner)
            normalized_phone = self._normalize_phone_number(phone_number)

            if not normalized_phone:
                _logger.error(f"No se pudo normalizar el número de teléfono: {phone_number}")
                return False

            _logger.info(f"Enviando recordatorio WhatsApp a {normalized_phone} para evento {calendar_event.id}")

            # Método 1: Usar WhatsApp directamente a través del partner
            try:
                # Intentar enviar mensaje directamente al partner
                vals = {
                    'body': message_body,
                    'number': normalized_phone,
                    'partner_id': partner.id,
                }

                # Usar el módulo de WhatsApp nativo de Odoo 18 directamente
                message = self.env['whatsapp.message'].create(vals)
                message.send_message()

                _logger.info(f"Mensaje WhatsApp enviado usando WhatsApp Message")
                return True

            except Exception as direct_error:
                _logger.warning(f"Error con envío directo: {direct_error}")

            # Método 2: Usar el método de la compañía
            try:
                company = self.env.company
                result = company._send_whatsapp({
                    'partner_id': partner.id,
                    'body': message_body,
                })

                if result:
                    _logger.info(f"Mensaje WhatsApp enviado usando método de compañía")
                    return True

            except Exception as company_error:
                _logger.warning(f"Error con método de compañía: {company_error}")

            # Método 3: API REST directa
            return self._send_via_rest_api(whatsapp_account, normalized_phone, message_body)

        except Exception as e:
            _logger.error(f"Error en _send_whatsapp_message_odoo18: {e}", exc_info=True)
            return False

    def _send_via_rest_api(self, whatsapp_account, phone_number, message_body):
        """
        Envía mensaje usando la API REST de WhatsApp directamente
        """
        try:
            import requests
            import json

            # Obtener configuración de la cuenta
            access_token = whatsapp_account.token
            phone_number_id = whatsapp_account.phone_uid

            if not access_token or not phone_number_id:
                _logger.error("Falta configuración de WhatsApp (token o phone_uid)")
                return False

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

            # Headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Limpiar número de teléfono (sin +)
            clean_phone = phone_number.lstrip('+')

            # Datos del mensaje
            data = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }

            _logger.info(f"Enviando vía API REST a {clean_phone}")

            # Realizar petición
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                _logger.info(f"Mensaje enviado exitosamente vía API REST: {response_data}")
                return True
            else:
                _logger.error(f"Error en API REST: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error en API REST: {e}")
            return False

    def _get_event_partner(self, calendar_event):
        """Obtiene el partner principal del evento"""
        # Buscar en los asistentes del evento
        for attendee in calendar_event.attendee_ids:
            if attendee.partner_id:
                return attendee.partner_id

        # Si no hay asistentes, buscar en el partner del evento
        if calendar_event.partner_ids:
            return calendar_event.partner_ids[0]

        return False

    def _get_partner_phone(self, partner):
        """Obtiene el número de teléfono del partner"""
        return partner.mobile or partner.phone

    def _normalize_phone_number(self, phone):
        """Normaliza el número de teléfono para WhatsApp"""
        if not phone:
            return False

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

    def _prepare_whatsapp_message(self, calendar_event):
        """Prepara el mensaje de recordatorio para WhatsApp"""
        # Usar mensaje predeterminado si no hay template
        return self._get_default_whatsapp_message(calendar_event)

    def _get_default_whatsapp_message(self, calendar_event):
        """Genera un mensaje predeterminado para el recordatorio"""
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

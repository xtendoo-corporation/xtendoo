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

            # Método 1: Intentar con composer simplificado
            try:
                composer = self.env['whatsapp.composer'].create({
                    'wa_account_id': whatsapp_account.id,
                    'partner_ids': [(6, 0, [partner.id])],
                    'body': message_body,
                })

                # Verificar si el método existe antes de llamarlo
                if hasattr(composer, 'action_send_whatsapp_message'):
                    composer.action_send_whatsapp_message()
                    _logger.info(f"Recordatorio WhatsApp enviado exitosamente usando composer")
                    return True
                else:
                    _logger.warning("Método action_send_whatsapp_message no disponible")

            except Exception as composer_error:
                _logger.warning(f"Error con composer: {composer_error}")

            # Método 2: Usar API directa si el composer falla
            return self._send_via_api_direct(whatsapp_account, normalized_phone, message_body, calendar_event)

        except Exception as e:
            _logger.error(f"Error en _send_whatsapp_message_odoo18: {e}", exc_info=True)
            return False

    def _send_via_api_direct(self, whatsapp_account, phone_number, message_body, calendar_event):
        """
        Envía mensaje usando la API directa de WhatsApp
        """
        try:
            # Intentar usar herramientas de WhatsApp de Odoo
            from odoo.addons.whatsapp.tools import whatsapp_api

            api_instance = whatsapp_api.WhatsAppApi(whatsapp_account)

            # Preparar datos del mensaje
            message_data = {
                'phone_number': phone_number,
                'message': message_body,
            }

            # Enviar mensaje
            result = api_instance.send_message(**message_data)

            if result and result.get('success', False):
                _logger.info(f"Mensaje WhatsApp enviado exitosamente vía API directa")
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response'
                _logger.error(f"Error en API directa: {error_msg}")
                return False

        except ImportError:
            _logger.error("No se pudo importar whatsapp_api")
            return False
        except Exception as e:
            _logger.error(f"Error en envío vía API directa: {e}")
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

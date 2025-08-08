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
        usando el mismo método que cuando se envía manualmente desde la interfaz
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

            # Primero intentar con el template configurado en la alarma
            template = self.whatsapp_template_id

            # Si no hay template configurado, buscar alguna plantilla para eventos
            if not template:
                _logger.info("No hay template configurado en la alarma, buscando uno predeterminado")
                # Buscar cualquier plantilla válida para eventos en este orden:
                template_names = ['Recordatorio de Cita Vitaltecuida 2', 'Recordatorio de Cita Vitaltecuida', 'Recordatorio de Cita']

                for name in template_names:
                    template = self.env['whatsapp.template'].search([
                        ('name', '=', name),
                        ('model', '=', 'calendar.event')
                    ], limit=1)
                    if template:
                        _logger.info(f"Encontrada plantilla por nombre: {name}")
                        break

                # Si no se encontró ninguna plantilla por nombre, buscar cualquier plantilla para eventos
                if not template:
                    _logger.warning("No se encontraron plantillas por nombre, buscando cualquier plantilla para eventos")
                    template = self.env['whatsapp.template'].search([
                        ('model', '=', 'calendar.event')
                    ], limit=1)

            if not template:
                _logger.error("No se encontró ninguna plantilla de WhatsApp para eventos")
                return False

            _logger.info(f"Usando plantilla: {template.name} [ID: {template.id}]")

            # Preparar contexto de renderizado
            ctx = calendar_event.get_whatsapp_reminder_context()
            _logger.info(f"Contexto de renderizado: {ctx}")

            # Crear un registro de compositor de WhatsApp igual que se hace en la interfaz
            composer_values = {
                'wa_template_id': template.id,
                'res_model': 'calendar.event',
                'res_ids': calendar_event.id,
                'phone': phone_number,
            }

            # Crear el compositor de WhatsApp
            composer = self.env['whatsapp.composer'].sudo().create(composer_values)
            _logger.info(f"Compositor creado con ID: {composer.id}")

            # Cargar la plantilla (esto generará el cuerpo del mensaje con los valores del evento)
            try:
                composer.onchange_template_id()
                _logger.info("Plantilla cargada correctamente en el compositor")
            except Exception as e:
                _logger.warning(f"Error al cargar la plantilla en el compositor: {e}")

            # Enviar el mensaje utilizando el método nativo
            try:
                result = composer.sudo().action_send_whatsapp_template()
                _logger.info(f"Mensaje enviado: {result}")

                # Marcar como enviado en el evento
                calendar_event.write({
                    'whatsapp_reminder_sent': True,
                    'whatsapp_reminder_date': fields.Datetime.now()
                })

                return True
            except Exception as e:
                _logger.error(f"Error al enviar el mensaje de WhatsApp: {e}", exc_info=True)
                # Si falla el compositor, intentar con fallback a mensaje directo básico
                message_body = self._get_default_whatsapp_message(calendar_event)
                return self._send_fallback_message(whatsapp_account, phone_number, message_body, calendar_event)

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

    def _send_fallback_message(self, whatsapp_account, phone_number, message_body, calendar_event):
        """Método simplificado para enviar mensaje como fallback cuando falla el compositor"""
        try:
            import requests
            import json

            # Verificar la cuenta de WhatsApp
            if not whatsapp_account or not whatsapp_account.token or not whatsapp_account.phone_uid:
                _logger.error("Falta configuración de WhatsApp")
                return False

            # Verificar el número de teléfono
            if not phone_number:
                _logger.error("No se proporcionó número de teléfono")
                return False

            # Limpiar número de teléfono (sin +)
            clean_phone = phone_number.lstrip('+')

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{whatsapp_account.phone_uid}/messages"

            # Headers
            headers = {
                'Authorization': f'Bearer {whatsapp_account.token}',
                'Content-Type': 'application/json'
            }

            # Datos del mensaje
            data = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }

            _logger.info(f"Enviando vía API REST fallback a {clean_phone}")

            # Realizar petición
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                _logger.info(f"Mensaje de fallback enviado exitosamente")

                # Marcar como enviado en el evento
                calendar_event.write({
                    'whatsapp_reminder_sent': True,
                    'whatsapp_reminder_date': fields.Datetime.now()
                })

                # Intentar registrar en el chatter
                try:
                    calendar_event.sudo().message_post(
                        body=f"<b>Mensaje WhatsApp enviado (fallback)</b><br/>{message_body.replace(chr(10), '<br/>')}",
                        subtype_id=self.env.ref('mail.mt_note').id,
                        message_type='comment',
                    )
                except Exception as chatter_error:
                    _logger.warning(f"Error al registrar mensaje en el chatter: {chatter_error}")

                return True
            else:
                _logger.error(f"Error en API REST fallback: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error en fallback: {e}", exc_info=True)
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

    def _get_default_whatsapp_message(self, calendar_event):
        """Genera un mensaje predeterminado para el recordatorio"""
        import pytz
        from datetime import datetime

        # Forzar el uso de zona horaria de Madrid
        local_tz = pytz.timezone('Europe/Madrid')

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

Si necesitas cancelar o reprogramar, por favor contáctanos con anticipación.

¡Te esperamos!

{self.env.company.name}"""

        return message

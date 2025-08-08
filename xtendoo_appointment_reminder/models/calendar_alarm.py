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
            phone_number = self._get_partner_phone(partner)
            normalized_phone = self._normalize_phone_number(phone_number)

            if not normalized_phone:
                _logger.error(f"No se pudo normalizar el número de teléfono: {phone_number}")
                return False

            _logger.info(f"Enviando recordatorio WhatsApp a {normalized_phone} para evento {calendar_event.id}")

            # Primero intentar usar la plantilla definida en XML
            try:
                # Buscar la plantilla por nombre
                template = self.env['whatsapp.template'].search([
                    ('name', '=', 'Recordatorio de Cita')
                ], limit=1)

                if template:
                    _logger.info(f"Usando plantilla 'Recordatorio de Cita' con ID {template.id}")
                    template_params = self._get_template_params(calendar_event)
                    return self._send_template_via_api(whatsapp_account, normalized_phone, template, template_params)
                else:
                    _logger.warning("No se encontró la plantilla 'Recordatorio de Cita' en la base de datos")
            except Exception as e:
                _logger.warning(f"Error buscando plantilla: {e}")

            # Si no se pudo usar la plantilla, intentar con mensaje directo
            _logger.info("Fallback a mensaje de texto directo")
            message_body = self._get_default_whatsapp_message(calendar_event)
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

            # Verificar la cuenta de WhatsApp
            if not whatsapp_account:
                _logger.error("No se proporcionó cuenta de WhatsApp")
                return False

            # Verificar campos necesarios en la cuenta
            account_info = f"ID: {whatsapp_account.id}, Nombre: {whatsapp_account.name}"
            _logger.info(f"Usando cuenta de WhatsApp: {account_info}")

            # Obtener configuración de la cuenta
            access_token = whatsapp_account.token
            phone_number_id = whatsapp_account.phone_uid

            # Verificar campos de la cuenta
            if not access_token:
                _logger.error(f"La cuenta de WhatsApp {account_info} no tiene token configurado")
                return False

            if not phone_number_id:
                _logger.error(f"La cuenta de WhatsApp {account_info} no tiene phone_uid configurado")
                return False

            # Verificar el número de teléfono
            if not phone_number:
                _logger.error("No se proporcionó número de teléfono")
                return False

            # Limpiar número de teléfono (sin +)
            clean_phone = phone_number.lstrip('+')

            # Verificar que el número tenga un formato válido
            if len(clean_phone) < 10:
                _logger.error(f"El número de teléfono {clean_phone} parece ser demasiado corto")
                return False

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

            # Headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Verificar el mensaje
            if not message_body:
                _logger.error("No se proporcionó cuerpo del mensaje")
                return False

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
            _logger.info(f"URL: {url}")
            _logger.info(f"Datos: {json.dumps(data, ensure_ascii=False)}")

            try:
                # Realizar petición
                response = requests.post(url, headers=headers, json=data, timeout=30)

                # Registrar la respuesta completa para diagnóstico
                _logger.info(f"Código de respuesta: {response.status_code}")
                _logger.info(f"Respuesta completa: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    _logger.info(f"Mensaje enviado exitosamente vía API REST: {response_data}")

                    # Verificar si la respuesta contiene el ID del mensaje
                    if 'messages' in response_data and response_data['messages']:
                        message_id = response_data['messages'][0].get('id')
                        _logger.info(f"ID del mensaje enviado: {message_id}")

                        # Guardar el registro del mensaje enviado utilizando el modelo nativo de Odoo
                        try:
                            if hasattr(self.env, 'whatsapp_message'):
                                self.env['whatsapp.message'].sudo().create({
                                    'name': f"Recordatorio para evento",
                                    'message_id': message_id,
                                    'mobile': clean_phone,
                                    'body': message_body,
                                    'status': 'sent',
                                })
                        except Exception as log_error:
                            _logger.warning(f"No se pudo registrar el mensaje en el historial: {log_error}")

                        # Intentar añadir un mensaje en el chatter del evento
                        try:
                            # Buscar el evento relacionado con este mensaje
                            # Primero intentamos obtener el evento desde el contexto
                            event = self.env.context.get('calendar_event')

                            # Si no está en el contexto, intentar encontrarlo por nombre/descripción en el mensaje
                            if not event:
                                # Extraer posibles identificadores del evento del mensaje
                                import re
                                event_identifier = None
                                # Buscar el asunto en el mensaje (normalmente después de *Asunto:*)
                                subject_match = re.search(r'\*Asunto:\*\s*([^\n]+)', message_body)
                                if subject_match:
                                    event_identifier = subject_match.group(1).strip()

                                if event_identifier:
                                    events = self.env['calendar.event'].sudo().search([
                                        '|',
                                        ('name', '=', event_identifier),
                                        ('id', '=', event_identifier if event_identifier.isdigit() else -1)
                                    ], limit=1)

                                    if events:
                                        event = events[0]

                            # Crear mensaje en el chatter si encontramos el evento
                            if event:
                                # Verificar si el modelo tiene campo message_ids (chatter)
                                if hasattr(event, 'message_post'):
                                    # Crear mensaje en el chatter
                                    event.sudo().message_post(
                                        body=f"<b>Mensaje WhatsApp enviado</b><br/>{message_body.replace(chr(10), '<br/>')}",
                                        subtype_id=self.env.ref('mail.mt_note').id,
                                        message_type='comment',
                                        author_id=self.env.user.partner_id.id
                                    )
                                    _logger.info(f"Mensaje registrado en el chatter del evento {event.name} (ID: {event.id})")
                        except Exception as chatter_error:
                            _logger.warning(f"Error al registrar mensaje en el chatter: {chatter_error}")

                    # Verificar el estado del contacto
                    if 'contacts' in response_data and response_data['contacts']:
                        contact_input = response_data['contacts'][0].get('input')
                        contact_wa_id = response_data['contacts'][0].get('wa_id')
                        _logger.info(f"Contacto - Número de entrada: {contact_input}, WhatsApp ID: {contact_wa_id}")

                    return True
                else:
                    _logger.error(f"Error en API REST: {response.status_code} - {response.text}")

                    # Intentar analizar la respuesta de error para más detalles
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_message = error_data['error'].get('message', 'Desconocido')
                            error_type = error_data['error'].get('type', 'Desconocido')
                            error_code = error_data['error'].get('code', 'Desconocido')
                            _logger.error(f"Detalles del error - Tipo: {error_type}, Código: {error_code}, Mensaje: {error_message}")

                            # Si es un error relacionado con restricciones de mensajería
                            if error_code in [130429, 131047, 131051]:
                                _logger.warning("Error de restricción de WhatsApp, intentando fallback a SMS")
                                return self._send_sms_fallback(phone_number, message_body)
                    except:
                        _logger.error("No se pudieron analizar los detalles del error")

                    return False
            except requests.exceptions.RequestException as req_error:
                _logger.error(f"Error en la petición HTTP: {req_error}")
                return False

        except Exception as e:
            _logger.error(f"Error en API REST: {e}", exc_info=True)
            return False

    def _test_message_reception(self, message_id, phone_number, whatsapp_account):
        """
        Envía un mensaje de diagnóstico para verificar si la cuenta puede enviar mensajes.
        Solo para fines de depuración durante la configuración inicial.
        """
        try:
            # Solo hacer esto durante la configuración inicial y luego deshabilitar
            debug_mode = self.env['ir.config_parameter'].sudo().get_param('whatsapp.debug_mode', 'false').lower() == 'true'
            if not debug_mode:
                return

            _logger.info(f"Enviando mensaje de prueba para diagnóstico...")

            # Intentar enviar un mensaje simple de diagnóstico
            import requests
            import json

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{whatsapp_account.phone_uid}/messages"

            # Headers
            headers = {
                'Authorization': f'Bearer {whatsapp_account.token}',
                'Content-Type': 'application/json'
            }

            # Plantilla de sistema (debería estar disponible por defecto)
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number.lstrip('+'),
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {"code": "en_US"}
                }
            }

            _logger.info(f"Enviando plantilla de prueba hello_world...")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            _logger.info(f"Respuesta de diagnóstico: {response.status_code} - {response.text}")

        except Exception as e:
            _logger.warning(f"Error en prueba de diagnóstico: {e}")

    def _send_sms_fallback(self, phone_number, message_body):
        """
        Envía un SMS como respaldo cuando WhatsApp falla
        """
        try:
            # Verificar si el módulo SMS está disponible
            if not self.env['ir.module.module'].search([('name', '=', 'sms'), ('state', '=', 'installed')]):
                _logger.warning("El módulo SMS no está instalado para usar como fallback")
                return False

            _logger.info(f"Intentando enviar SMS de respaldo a {phone_number}")

            # Preparar un mensaje SMS más corto
            sms_body = message_body
            if len(message_body) > 160:
                # Acortar el mensaje para SMS
                sms_body = message_body[:157] + "..."

            # Enviar SMS usando el módulo nativo de Odoo
            sms_api = self.env['sms.api']
            result = sms_api.send_sms([phone_number], sms_body)

            if result:
                _logger.info(f"SMS de respaldo enviado exitosamente a {phone_number}")
                return True
            else:
                _logger.warning(f"Fallo al enviar SMS de respaldo")
                return False

        except Exception as e:
            _logger.error(f"Error en fallback a SMS: {e}")
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
        # Si hay una plantilla configurada, intentar procesarla con la API
        if self.whatsapp_template_id:
            try:
                # Obtener el partner asociado al evento
                partner = self._get_event_partner(calendar_event)
                if not partner:
                    _logger.warning(f"No se encontró partner para el evento {calendar_event.name}")
                    return self._get_default_whatsapp_message(calendar_event)

                # Buscar cuenta de WhatsApp activa
                whatsapp_account = self._get_whatsapp_account()
                if not whatsapp_account:
                    _logger.warning("No se encontró cuenta de WhatsApp para enviar plantilla")
                    return self._get_default_whatsapp_message(calendar_event)

                # Obtener los datos necesarios para la plantilla
                template = self.whatsapp_template_id

                # Extraer parámetros para la plantilla
                template_params = self._get_template_params(calendar_event)

                # Usar directamente la API de WhatsApp (Facebook API) para enviar la plantilla
                phone_number = self._get_partner_phone(partner)
                normalized_phone = self._normalize_phone_number(phone_number)

                if not normalized_phone:
                    return self._get_default_whatsapp_message(calendar_event)

                # Enviar plantilla usando API REST
                success = self._send_template_via_api(whatsapp_account, normalized_phone, template, template_params)

                if success:
                    _logger.info(f"Plantilla WhatsApp enviada exitosamente para evento {calendar_event.name}")
                    return True
                else:
                    _logger.warning(f"Error al enviar plantilla, usando mensaje por defecto")

            except Exception as e:
                _logger.warning(f"Error al usar plantilla WhatsApp: {e}")

        # Usar mensaje predeterminado si no hay plantilla o si falló el envío
        return self._get_default_whatsapp_message(calendar_event)

    def _send_template_via_api(self, whatsapp_account, phone_number, template, params):
        """
        Envía una plantilla de WhatsApp usando la API directa
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

            # Nombre exacto de la plantilla como está aprobado en Facebook
            template_name = "recordatorio_de_cita"  # Asegúrate de que este es el nombre exacto en Facebook

            # Extraer el ID del evento directamente desde params
            event_id = None
            if isinstance(params, dict) and '2' in params:
                if isinstance(params['2'], int):
                    event_id = params['2']
                else:
                    try:
                        # Intentar convertir a entero si es posible
                        event_id = int(params['2'])
                    except (ValueError, TypeError):
                        # Si no es un entero, podría ser el nombre del evento
                        pass

            # Intentar primero con mensaje directo (esto es más confiable)
            try:
                # Construir un mensaje de texto básico con los parámetros disponibles
                message_body = f"""📅 *Recordatorio de Cita*

Hola {params.get('1', 'Estimado cliente')},

Te recordamos tu cita programada:

📋 *Asunto:* {params.get('2', 'Cita')}
📅 *Fecha:* {params.get('3', 'Por confirmar')}
🕐 *Hora:* {params.get('4', 'Por confirmar')}
📍 *Ubicación:* {params.get('5', 'Por confirmar')}

Si necesitas cancelar o reprogramar, por favor contáctanos con anticipación.

¡Te esperamos!

{params.get('7', self.env.company.name)}"""

                direct_success = self._send_via_rest_api(whatsapp_account, phone_number, message_body)
                if direct_success:
                    _logger.info("Mensaje de texto enviado exitosamente como alternativa a la plantilla")
                    return True
            except Exception as direct_error:
                _logger.warning(f"Error enviando mensaje directo: {direct_error}")

            # Preparar los parámetros para los componentes de la plantilla
            components = []
            component_params = []

            # Asegurar que tenemos todos los parámetros necesarios (exactamente 7)
            required_params = {
                '1': params.get('1', 'Estimado cliente'),     # Nombre del cliente
                '2': params.get('2', 'Evento'),               # Nombre del evento
                '3': params.get('3', 'Por confirmar'),        # Fecha
                '4': params.get('4', 'Por confirmar'),        # Hora
                '5': params.get('5', 'Por confirmar'),        # Ubicación
                '6': params.get('6', ''),                     # Descripción
                '7': params.get('7', self.env.company.name)   # Empresa
            }

            # Añadir los parámetros en orden
            for i in range(1, 8):  # Del 1 al 7, según la plantilla
                key = str(i)
                component_params.append({
                    "type": "text",
                    "text": required_params[key]
                })

            if component_params:
                components.append({
                    "type": "body",
                    "parameters": component_params
                })

            # Ahora intentar con diferentes códigos de idioma
            language_codes = ["en_US", "en", "es", "es_ES", ""]

            for lang_code in language_codes:
                try:
                    # Datos para la solicitud de la plantilla
                    data = {
                        "messaging_product": "whatsapp",
                        "to": clean_phone,
                        "type": "template",
                        "template": {
                            "name": template_name,
                            "language": {"code": lang_code or "en_US"},
                            "components": components
                        }
                    }

                    _logger.info(f"Enviando plantilla {template_name} vía API REST con idioma '{lang_code}' a {clean_phone}")
                    _logger.info(f"URL: {url}")
                    _logger.info(f"Datos de la plantilla: {json.dumps(data, ensure_ascii=False)}")

                    # Realizar petición
                    response = requests.post(url, headers=headers, json=data, timeout=30)

                    # Registrar la respuesta completa para diagnóstico
                    _logger.info(f"Código de respuesta: {response.status_code}")
                    _logger.info(f"Respuesta completa: {response.text}")

                    if response.status_code == 200:
                        response_data = response.json()
                        _logger.info(f"Plantilla enviada exitosamente con idioma {lang_code}: {response_data}")
                        return True

                    # Analizar el error
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_code = error_data['error'].get('code')
                            error_message = error_data['error'].get('message')

                            # Si es un error de plantilla, seguir intentando con otro idioma
                            if error_code == 132001:  # Error de plantilla no existe en ese idioma
                                _logger.warning(f"La plantilla no existe en el idioma {lang_code}, probando otro")
                                continue
                            else:
                                # Si es otro tipo de error, registrar y continuar intentando
                                _logger.error(f"Error no relacionado con el idioma: {error_message}")
                    except Exception as e:
                        _logger.error(f"Error al procesar respuesta de error: {e}")

                except Exception as e:
                    _logger.error(f"Error al intentar con idioma {lang_code}: {e}")

            # Si llegamos aquí, ningún idioma funcionó, usar mensaje de texto como último recurso
            _logger.warning("Ningún idioma funcionó para la plantilla, enviando mensaje de texto normal")
            return self._send_via_rest_api(whatsapp_account, phone_number, message_body)

        except Exception as e:
            _logger.error(f"Error enviando plantilla: {e}")
            # Si falla todo, intentar enviar mensaje directo
            try:
                # Construir un mensaje de texto básico con los parámetros disponibles
                message_body = f"""📅 *Recordatorio de Cita*

Hola {params.get('1', 'Estimado cliente')},

Te recordamos tu cita programada:

📋 *Asunto:* {params.get('2', 'Cita')}
📅 *Fecha:* {params.get('3', 'Por confirmar')}
🕐 *Hora:* {params.get('4', 'Por confirmar')}
📍 *Ubicación:* {params.get('5', 'Por confirmar')}

Si necesitas cancelar o reprogramar, por favor contáctanos con anticipación.

¡Te esperamos!

{params.get('7', self.env.company.name)}"""

                return self._send_via_rest_api(whatsapp_account, phone_number, message_body)
            except Exception as final_error:
                _logger.error(f"Error en el último intento: {final_error}")
                return False

    def _get_template_params(self, calendar_event):
        """
        Prepara los parámetros para la plantilla de WhatsApp
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

        # Nombre del cliente
        partner = self._get_event_partner(calendar_event)
        client_name = partner.name if partner else "Estimado cliente"

        # Información de ubicación
        location = calendar_event.location or "ubicación por confirmar"
        description = calendar_event.description or ""
        company_name = self.env.company.name

        # Parámetros para la plantilla (ajustar según la estructura de tu plantilla)
        return {
            "1": client_name,                 # Nombre del cliente
            "2": calendar_event.name,         # Nombre del evento
            "3": date_str,                    # Fecha
            "4": time_str,                    # Hora
            "5": location,                    # Ubicación
            "6": description,                 # Descripción
            "7": company_name                 # Nombre de la empresa
        }

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

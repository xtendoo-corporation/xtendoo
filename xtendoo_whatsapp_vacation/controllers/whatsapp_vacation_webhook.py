import logging
import json
import re
from datetime import datetime, timedelta
from dateutil.parser import parse as date_parse

from odoo import http
from odoo.http import request
from odoo.addons.whatsapp.controller.main import Webhook

_logger = logging.getLogger(__name__)


class WhatsAppVacationWebhook(Webhook):
    """
    Controlador que hereda de Webhook para gestionar solicitudes de vacaciones por WhatsApp
    """

    @http.route('/whatsapp/webhook/', methods=['POST'], type="json", auth="public")
    def webhookpost(self):
        """
        Método heredado que procesa mensajes de WhatsApp y gestiona solicitudes de vacaciones
        """
        print("="*80)
        print("🏖️ XTENDOO WHATSAPP VACATION - MENSAJE RECIBIDO (POST)")
        print("="*80)

        # Obtener datos de la petición
        raw_data = request.httprequest.data
        data = json.loads(raw_data)

        print(f"Método HTTP: {request.httprequest.method}")
        print(f"URL completa: {request.httprequest.url}")
        print(f"Content-Type: {request.httprequest.content_type}")

        # Procesar mensajes para solicitudes de vacaciones
        self._process_vacation_messages(data)

        # Llamar al método original para mantener la funcionalidad
        try:
            result = super().webhookpost()
            print("✅ Procesamiento original completado exitosamente")
            print("="*80)
            return result
        except Exception as e:
            print(f"❌ Error en procesamiento original: {e}")
            print("="*80)
            raise

    def _process_vacation_messages(self, data):
        """
        Procesa los mensajes de WhatsApp para detectar comandos de vacaciones
        """
        print("\n🏖️ --- PROCESAMIENTO DE SOLICITUDES DE VACACIONES ---")

        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})

                        # Procesar mensajes recibidos
                        for message in value.get('messages', []):
                            if message.get('type') == 'text':
                                self._handle_vacation_message(message, value)

        except Exception as e:
            print(f"❌ Error procesando vacaciones: {e}")
            _logger.error("Error en procesamiento de vacaciones: %s", e)

    def _handle_vacation_message(self, message, value):
        """
        Maneja un mensaje de texto individual para detectar comandos de vacaciones
        """
        try:
            phone_number = message.get('from', '')
            text_content = message.get('text', {}).get('body', '').strip()

            print(f"\n📋 Procesando mensaje de vacaciones:")
            print(f"   Teléfono: {phone_number}")
            print(f"   Texto: '{text_content}'")

            # Verificar si el usuario quiere cancelar
            if self._is_cancel_command(text_content):
                self._cancel_vacation_process(phone_number)
                return

            # Buscar empleado por número de teléfono
            employee = self._find_employee_by_phone(phone_number)
            if not employee:
                return

            # Verificar si hay un proceso de vacaciones en curso
            vacation_state = self._get_vacation_state(phone_number)

            if vacation_state:
                # Continuar con el proceso existente
                self._continue_vacation_process(phone_number, employee, text_content, vacation_state)
            else:
                # Detectar comando de inicio de vacaciones
                if self._detect_vacation_command(text_content):
                    print(f"✅ Comando de vacaciones detectado")
                    self._start_vacation_process(phone_number, employee)

        except Exception as e:
            print(f"❌ Error manejando mensaje de vacaciones: {e}")
            _logger.error("Error manejando mensaje de vacaciones: %s", e)

    def _detect_vacation_command(self, text):
        """
        Detecta si el texto contiene un comando de vacaciones válido
        """
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Obtener palabras clave desde configuración
        vacation_keywords = request.env['vacation.keyword.config'].sudo().get_active_vacation_keywords()

        print(f"🔍 Palabras clave de vacaciones: {vacation_keywords}")

        for keyword in vacation_keywords:
            keyword_lower = keyword.lower()

            # Patrones de búsqueda flexibles
            patterns = [
                r'^' + re.escape(keyword_lower) + r'$',  # Coincidencia exacta
                r'^' + re.escape(keyword_lower) + r'\s',  # Al inicio seguido de espacio
                r'\s' + re.escape(keyword_lower) + r'$',  # Al final precedido de espacio
                r'\s' + re.escape(keyword_lower) + r'\s'  # En medio con espacios
            ]

            for pattern in patterns:
                if re.search(pattern, normalized_text):
                    print(f"✅ Coincidencia encontrada: '{keyword}'")
                    return True

            # También buscar coincidencia simple
            if keyword_lower == normalized_text or keyword_lower in normalized_text:
                print(f"✅ Coincidencia simple: '{keyword}'")
                return True

        return False

    def _is_cancel_command(self, text):
        """
        Verifica si el mensaje es un comando de cancelación
        """
        cancel_commands = ['/cancelar', 'cancelar', '/cancel', 'cancel']
        normalized_text = text.lower().strip()
        return normalized_text in cancel_commands

    def _start_vacation_process(self, phone_number, employee):
        """
        Inicia el proceso de solicitud de vacaciones
        """
        print(f"🏖️ Iniciando proceso de vacaciones para {employee.name}")

        # Guardar estado inicial
        self._set_vacation_state(phone_number, {
            'step': 'asking_days',
            'employee_id': employee.id,
            'started_at': datetime.now().isoformat()
        })

        # Enviar mensaje preguntando por los días
        message = (
            f"🏖️ ¡Hola {employee.name}!\n\n"
            "Vamos a procesar tu solicitud de vacaciones.\n\n"
            "📅 **¿Cuántos días de vacaciones quieres solicitar?**\n\n"
            "• Responde solo con el número (ej: 5)\n"
            "• Para cancelar en cualquier momento escribe: `/cancelar`\n\n"
            "✨ ¡Estoy aquí para ayudarte!"
        )

        self._send_whatsapp_message(phone_number, message)

    def _continue_vacation_process(self, phone_number, employee, text_content, vacation_state):
        """
        Continúa con el proceso de solicitud según el paso actual
        """
        step = vacation_state.get('step')

        if step == 'asking_days':
            self._handle_days_response(phone_number, employee, text_content, vacation_state)
        elif step == 'asking_dates':
            self._handle_dates_response(phone_number, employee, text_content, vacation_state)
        elif step == 'asking_end_date':
            self._handle_end_date_response(phone_number, employee, text_content, vacation_state)

    def _handle_days_response(self, phone_number, employee, text_content, vacation_state):
        """
        Procesa la respuesta de cuántos días de vacaciones
        """
        try:
            # Extraer número de días
            days_match = re.search(r'\d+', text_content.strip())
            if not days_match:
                self._send_whatsapp_message(
                    phone_number,
                    "❌ No pude entender el número de días.\n\n"
                    "Por favor responde solo con el número (ej: 5)\n"
                    "Para cancelar escribe: `/cancelar`"
                )
                return

            days = int(days_match.group())

            # Validar días mínimos y máximos
            if days <= 0:
                self._send_whatsapp_message(
                    phone_number,
                    "❌ El número de días debe ser mayor a 0.\n\n"
                    "Por favor indica cuántos días quieres solicitar.\n"
                    "Para cancelar escribe: `/cancelar`"
                )
                return

            if days > 30:
                self._send_whatsapp_message(
                    phone_number,
                    "⚠️ Solicitas muchos días de vacaciones (más de 30).\n\n"
                    "Por favor verifica el número o contacta con Recursos Humanos.\n"
                    "Para cancelar escribe: `/cancelar`"
                )
                return

            # Actualizar estado con los días
            vacation_state['days'] = days
            vacation_state['step'] = 'asking_dates'
            self._set_vacation_state(phone_number, vacation_state)

            # Preguntar por las fechas
            if days == 1:
                message = (
                    f"✅ Perfecto, solicitas **{days} día** de vacaciones.\n\n"
                    "📅 **¿Para qué fecha?**\n\n"
                    "Escribe la fecha en formato: **DD/MM/YYYY**\n"
                    "Ejemplo: 15/08/2024\n\n"
                    "Para cancelar escribe: `/cancelar`"
                )
            else:
                message = (
                    f"✅ Perfecto, solicitas **{days} días** de vacaciones.\n\n"
                    "📅 **¿Cuál es la fecha de inicio?**\n\n"
                    "Escribe la fecha en formato: **DD/MM/YYYY**\n"
                    "Ejemplo: 15/08/2024\n\n"
                    "Para cancelar escribe: `/cancelar`"
                )

            self._send_whatsapp_message(phone_number, message)

        except Exception as e:
            print(f"❌ Error procesando días: {e}")
            self._send_error_message(phone_number, "Error procesando el número de días")

    def _handle_dates_response(self, phone_number, employee, text_content, vacation_state):
        """
        Procesa la respuesta de la fecha de inicio
        """
        try:
            # Intentar parsear la fecha
            date_start = self._parse_date(text_content.strip())
            if not date_start:
                self._send_whatsapp_message(
                    phone_number,
                    "❌ No pude entender la fecha.\n\n"
                    "Por favor usa el formato: **DD/MM/YYYY**\n"
                    "Ejemplo: 15/08/2024\n\n"
                    "Para cancelar escribe: `/cancelar`"
                )
                return

            # Validar que la fecha no sea en el pasado
            if date_start < datetime.now().date():
                self._send_whatsapp_message(
                    phone_number,
                    "❌ La fecha no puede ser en el pasado.\n\n"
                    "Por favor indica una fecha futura.\n"
                    "Formato: **DD/MM/YYYY**\n\n"
                    "Para cancelar escribe: `/cancelar`"
                )
                return

            # Actualizar estado con fecha de inicio
            vacation_state['date_from'] = date_start.isoformat()
            days = vacation_state['days']

            if days == 1:
                # Solo un día, usar la misma fecha para inicio y fin
                vacation_state['date_to'] = date_start.isoformat()
                vacation_state['step'] = 'ready_to_create'
                self._create_vacation_request(phone_number, employee, vacation_state)
            else:
                # Múltiples días, calcular fecha de fin automáticamente
                date_end = date_start + timedelta(days=days-1)
                vacation_state['date_to'] = date_end.isoformat()
                vacation_state['step'] = 'asking_end_date'

                self._set_vacation_state(phone_number, vacation_state)

                message = (
                    f"✅ Fecha de inicio: **{date_start.strftime('%d/%m/%Y')}**\n\n"
                    f"📅 La fecha de fin calculada sería: **{date_end.strftime('%d/%m/%Y')}**\n\n"
                    "¿Es correcta esta fecha de fin?\n"
                    "• Responde **SÍ** para confirmar\n"
                    "• O escribe una fecha diferente en formato **DD/MM/YYYY**\n\n"
                    "Para cancelar escribe: `/cancelar`"
                )

                self._send_whatsapp_message(phone_number, message)

        except Exception as e:
            print(f"❌ Error procesando fecha: {e}")
            self._send_error_message(phone_number, "Error procesando la fecha")

    def _handle_end_date_response(self, phone_number, employee, text_content, vacation_state):
        """
        Procesa la respuesta de confirmación de fecha de fin
        """
        try:
            response = text_content.strip().lower()

            if response in ['sí', 'si', 'yes', 'ok', 'correcto', 'bien']:
                # Confirmar con fecha calculada
                self._create_vacation_request(phone_number, employee, vacation_state)
            else:
                # Intentar parsear nueva fecha
                new_date_end = self._parse_date(text_content.strip())
                if not new_date_end:
                    self._send_whatsapp_message(
                        phone_number,
                        "❌ No pude entender la respuesta.\n\n"
                        "Responde **SÍ** para confirmar la fecha propuesta\n"
                        "O escribe una nueva fecha en formato **DD/MM/YYYY**\n\n"
                        "Para cancelar escribe: `/cancelar`"
                    )
                    return

                # Validar nueva fecha
                date_start = datetime.fromisoformat(vacation_state['date_from']).date()
                if new_date_end < date_start:
                    self._send_whatsapp_message(
                        phone_number,
                        f"❌ La fecha de fin no puede ser anterior a la fecha de inicio ({date_start.strftime('%d/%m/%Y')}).\n\n"
                        "Por favor indica una fecha válida.\n"
                        "Para cancelar escribe: `/cancelar`"
                    )
                    return

                # Actualizar con nueva fecha de fin
                vacation_state['date_to'] = new_date_end.isoformat()
                self._create_vacation_request(phone_number, employee, vacation_state)

        except Exception as e:
            print(f"❌ Error procesando fecha de fin: {e}")
            self._send_error_message(phone_number, "Error procesando la fecha de fin")

    def _create_vacation_request(self, phone_number, employee, vacation_state):
        """
        Crea la solicitud de vacaciones en Odoo
        """
        try:
            print(f"🏖️ Creando solicitud de vacaciones para {employee.name}")

            date_from = datetime.fromisoformat(vacation_state['date_from']).date()
            date_to = datetime.fromisoformat(vacation_state['date_to']).date()
            days = vacation_state['days']

            # Buscar tipo de ausencia para vacaciones
            holiday_type = request.env['hr.leave.type'].sudo().search([
                ('code', '=', 'VACATION')
            ], limit=1)

            if not holiday_type:
                holiday_type = request.env['hr.leave.type'].sudo().search([
                    ('name', 'ilike', 'vacation')
                ], limit=1)

            if not holiday_type:
                holiday_type = request.env['hr.leave.type'].sudo().search([], limit=1)

            if not holiday_type:
                raise Exception("No se encontró tipo de ausencia configurado")

            # Crear la solicitud de vacaciones
            vacation_request = request.env['hr.leave'].sudo().create({
                'name': f'Solicitud de vacaciones via WhatsApp - {employee.name}',
                'employee_id': employee.id,
                'holiday_status_id': holiday_type.id,
                'date_from': datetime.combine(date_from, datetime.min.time()),
                'date_to': datetime.combine(date_to, datetime.max.time()),
                'number_of_days': days,
                'request_date_from': date_from,
                'request_date_to': date_to,
                'notes': f'Solicitud creada automáticamente via WhatsApp el {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                'state': 'confirm'  # Estado "To Approve"
            })

            print(f"✅ Solicitud creada con ID: {vacation_request.id}")

            # Limpiar estado
            self._clear_vacation_state(phone_number)

            # Enviar mensaje de confirmación
            message = (
                f"🎉 **¡Solicitud creada exitosamente!**\n\n"
                f"📋 **Detalles de tu solicitud:**\n"
                f"• Empleado: {employee.name}\n"
                f"• Días solicitados: {days}\n"
                f"• Fecha inicio: {date_from.strftime('%d/%m/%Y')}\n"
                f"• Fecha fin: {date_to.strftime('%d/%m/%Y')}\n"
                f"• Estado: Pendiente de aprobación\n\n"
                f"📝 **Número de solicitud:** {vacation_request.id}\n\n"
                "Tu solicitud ha sido enviada a Recursos Humanos para su revisión.\n"
                "¡Te notificaremos cuando sea aprobada! 🏖️"
            )

            self._send_whatsapp_message(phone_number, message)

        except Exception as e:
            print(f"❌ Error creando solicitud: {e}")
            self._send_error_message(phone_number, f"Error creando la solicitud de vacaciones: {str(e)}")
            self._clear_vacation_state(phone_number)

    def _cancel_vacation_process(self, phone_number):
        """
        Cancela el proceso de solicitud de vacaciones en curso
        """
        vacation_state = self._get_vacation_state(phone_number)
        if vacation_state:
            self._clear_vacation_state(phone_number)
            self._send_whatsapp_message(
                phone_number,
                "❌ **Proceso cancelado**\n\n"
                "Tu solicitud de vacaciones ha sido cancelada.\n"
                "Puedes iniciar una nueva cuando gustes escribiendo `/vacaciones`"
            )
        else:
            self._send_whatsapp_message(
                phone_number,
                "ℹ️ No hay ningún proceso de vacaciones activo para cancelar."
            )

    def _parse_date(self, date_string):
        """
        Intenta parsear una fecha desde diferentes formatos
        """
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%d/%m/%y',
            '%d-%m-%y',
            '%d.%m.%y'
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(date_string, date_format).date()
            except ValueError:
                continue

        return None

    def _find_employee_by_phone(self, phone_number):
        """
        Busca un empleado por su número de teléfono (reutilizado del módulo de asistencias)
        """
        try:
            def normalize_phone(phone):
                if not phone:
                    return ""
                clean = re.sub(r'[^\d]', '', str(phone))
                if len(clean) > 9:
                    country_codes_2 = ['34', '52', '54', '57', '58', '51', '56', '55', '33', '49', '44', '39']
                    country_codes_1 = ['1']

                    for code in country_codes_2:
                        if clean.startswith(code) and len(clean) >= len(code) + 9:
                            return clean[len(code):]

                    for code in country_codes_1:
                        if clean.startswith(code) and len(clean) >= len(code) + 10:
                            return clean[len(code):]

                return clean

            normalized_incoming = normalize_phone(phone_number)

            employees = request.env['hr.employee'].sudo().search([
                '|',
                ('mobile_phone', '!=', False),
                ('work_phone', '!=', False)
            ])

            for employee in employees:
                mobile_normalized = normalize_phone(employee.mobile_phone)
                work_normalized = normalize_phone(employee.work_phone)

                if (normalized_incoming and
                    (normalized_incoming == mobile_normalized or
                     normalized_incoming == work_normalized)):
                    return employee

                if len(normalized_incoming) >= 9:
                    local_incoming = normalized_incoming[-9:]
                    if len(mobile_normalized) >= 9 and local_incoming == mobile_normalized[-9:]:
                        return employee
                    if len(work_normalized) >= 9 and local_incoming == work_normalized[-9:]:
                        return employee

            return None

        except Exception as e:
            print(f"❌ Error buscando empleado: {e}")
            return None

    def _get_vacation_state(self, phone_number):
        """
        Obtiene el estado actual del proceso de vacaciones para un número
        """
        try:
            state_key = f'whatsapp_vacation_state_{phone_number}'
            state_json = request.env['ir.config_parameter'].sudo().get_param(state_key)
            if state_json:
                return json.loads(state_json)
            return None
        except Exception as e:
            print(f"❌ Error obteniendo estado: {e}")
            return None

    def _set_vacation_state(self, phone_number, state):
        """
        Guarda el estado del proceso de vacaciones
        """
        try:
            state_key = f'whatsapp_vacation_state_{phone_number}'
            state_json = json.dumps(state)
            request.env['ir.config_parameter'].sudo().set_param(state_key, state_json)
        except Exception as e:
            print(f"❌ Error guardando estado: {e}")

    def _clear_vacation_state(self, phone_number):
        """
        Limpia el estado del proceso de vacaciones
        """
        try:
            state_key = f'whatsapp_vacation_state_{phone_number}'
            request.env['ir.config_parameter'].sudo().set_param(state_key, False)
        except Exception as e:
            print(f"❌ Error limpiando estado: {e}")

    def _send_whatsapp_message(self, phone_number, message):
        """
        Envía un mensaje de WhatsApp
        """
        try:
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            # Implementar envío de mensaje (similar al módulo de asistencias)
            import requests

            access_token = None
            token_fields = ['access_token', 'token', 'app_secret', 'permanent_access_token']

            for field in token_fields:
                if hasattr(wa_account, field):
                    token_value = getattr(wa_account, field)
                    if token_value:
                        access_token = token_value
                        break

            if not access_token:
                return False

            url = f"https://graph.facebook.com/v18.0/{wa_account.phone_uid}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            clean_phone = phone_number.lstrip('+')
            data = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False

    def _send_error_message(self, phone_number, error_message):
        """
        Envía mensaje de error al usuario
        """
        message = f"❌ **Error**\n\n{error_message}\n\nPor favor, contacta con Recursos Humanos si el problema persiste."
        self._send_whatsapp_message(phone_number, message)

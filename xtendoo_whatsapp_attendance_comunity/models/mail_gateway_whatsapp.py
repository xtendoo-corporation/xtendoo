# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import re
from datetime import datetime

import pytz

from odoo import _, models

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappAttendance(models.AbstractModel):
    """
    Hereda del servicio de WhatsApp Gateway para procesar mensajes de asistencia
    """
    _inherit = "mail.gateway.whatsapp"

    def _process_update(self, chat, message, value):
        """
        Override del método _process_update para interceptar mensajes de asistencia
        antes del procesamiento normal
        """
        # Verificar si es un mensaje de asistencia
        if self._is_attendance_message(message):
            attendance_processed = self._handle_attendance_message(chat, message, value)
            if attendance_processed:
                # Si fue procesado como asistencia, no continuar con el procesamiento normal
                return

        # Si no es mensaje de asistencia o no se pudo procesar, continuar normalmente
        return super()._process_update(chat, message, value)

    def _is_attendance_message(self, message):
        """
        Verifica si el mensaje es un comando de asistencia
        """
        if message.get('type') not in ['text', 'location']:
            return False

        if message.get('type') == 'location':
            # Verificar si hay una solicitud de ubicación pendiente
            phone_number = message.get('from', '')
            pending_key = f'whatsapp_attendance_pending_{phone_number}'
            pending_data = self.env['ir.config_parameter'].sudo().get_param(pending_key)
            return bool(pending_data)

        if message.get('type') == 'text':
            text_content = message.get('text', {}).get('body', '').strip().lower()
            attendance_type = self._detect_attendance_command(text_content)
            return attendance_type is not None

        return False

    def _detect_attendance_command(self, text):
        """
        Detecta si el texto contiene un comando de asistencia válido
        Retorna 'check_in', 'check_out' o None
        """
        # Normalizar texto
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Obtener palabras clave de entrada desde configuración
        entrada_keywords = self.env['attendance.keyword.config'].sudo().get_active_keywords('check_in')
        salida_keywords = self.env['attendance.keyword.config'].sudo().get_active_keywords('check_out')

        _logger.debug(f"Palabras clave entrada: {entrada_keywords}")
        _logger.debug(f"Palabras clave salida: {salida_keywords}")

        # Buscar patrones de entrada
        for keyword in entrada_keywords:
            keyword_lower = keyword.lower()
            if self._keyword_matches(keyword_lower, normalized_text):
                _logger.info(f"Comando de ENTRADA detectado: '{keyword}'")
                return 'check_in'

        # Buscar patrones de salida
        for keyword in salida_keywords:
            keyword_lower = keyword.lower()
            if self._keyword_matches(keyword_lower, normalized_text):
                _logger.info(f"Comando de SALIDA detectado: '{keyword}'")
                return 'check_out'

        return None

    def _keyword_matches(self, keyword, text):
        """
        Verifica si la palabra clave coincide con el texto
        """
        # Para palabras clave con caracteres especiales
        if keyword.startswith('/') or keyword.startswith('#') or keyword.startswith('!'):
            patterns = [
                r'^' + re.escape(keyword) + r'$',
                r'^' + re.escape(keyword) + r'\s',
                r'\s' + re.escape(keyword) + r'$',
                r'\s' + re.escape(keyword) + r'\s'
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return True
        else:
            # Para palabras normales
            if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                return True

        # Coincidencia simple
        return keyword == text or keyword in text

    def _handle_attendance_message(self, chat, message, value):
        """
        Maneja un mensaje de asistencia
        """
        try:
            phone_number = message.get('from', '')

            # Si es un mensaje de ubicación, procesarlo
            if message.get('type') == 'location':
                return self._process_location_response(chat, phone_number, message)

            # Procesar mensaje de texto
            text_content = message.get('text', {}).get('body', '').strip().lower()
            attendance_type = self._detect_attendance_command(text_content)

            if not attendance_type:
                return False

            # Buscar empleado por teléfono del partner del canal
            employee = self._find_employee_by_channel(chat)

            if not employee:
                # Intentar buscar por número de teléfono
                employee = self._find_employee_by_phone(phone_number)

            if not employee:
                _logger.warning(f"No se encontró empleado para el teléfono: {phone_number}")
                self._send_error_response(chat, "No se encontró empleado asociado a este número")
                return True

            _logger.info(f"Empleado encontrado: {employee.name} (ID: {employee.id})")

            # Validar estado de asistencia
            validation_result = self._validate_attendance_state(employee, attendance_type)
            if not validation_result['valid']:
                _logger.warning(f"Validación fallida: {validation_result['message']}")
                self._send_error_response(chat, validation_result['message'])
                return True

            # Verificar si tiene geolocalización activada
            if employee.whatsapp_geotrack_enabled:
                _logger.info(f"Geolocalización activada para {employee.name}")
                self._request_location_for_attendance(chat, phone_number, employee, attendance_type, validation_result)
                return True

            # Registrar asistencia sin geolocalización
            attendance_result = self._register_attendance(employee, attendance_type, validation_result)

            if attendance_result:
                _logger.info(f"Asistencia registrada exitosamente para {employee.name}")
                self._send_confirmation_response(chat, attendance_type, employee)
            else:
                self._send_error_response(chat, "Error al registrar asistencia")

            return True

        except Exception as e:
            _logger.error(f"Error manejando mensaje de asistencia: {e}")
            return False

    def _find_employee_by_channel(self, chat):
        """
        Busca un empleado por el partner asociado al canal del gateway
        """
        try:
            # Obtener el partner del canal
            partner = None
            if hasattr(chat, 'channel_member_ids'):
                for member in chat.channel_member_ids:
                    if member.partner_id and member.partner_id != self.env.user.partner_id:
                        partner = member.partner_id
                        break

            if not partner:
                return None

            # Buscar empleado por partner
            employee = self.env['hr.employee'].sudo().search([
                ('work_contact_id', '=', partner.id)
            ], limit=1)

            if not employee:
                # Buscar por dirección de trabajo similar o por teléfono móvil
                if partner.mobile:
                    employee = self._find_employee_by_phone(partner.mobile)
                if not employee and partner.phone:
                    employee = self._find_employee_by_phone(partner.phone)

            return employee

        except Exception as e:
            _logger.error(f"Error buscando empleado por canal: {e}")
            return None

    def _find_employee_by_phone(self, phone_number):
        """
        Busca un empleado por su número de teléfono/WhatsApp
        """
        try:
            def normalize_phone(phone):
                if not phone:
                    return ""
                clean = re.sub(r'[^\d]', '', str(phone))
                # Códigos de país comunes
                if len(clean) > 9:
                    country_codes_2 = ['34', '52', '54', '57', '58', '51', '56', '55', '33', '49', '44', '39']
                    for code in country_codes_2:
                        if clean.startswith(code) and len(clean) >= len(code) + 9:
                            return clean[len(code):]
                    if clean.startswith('1') and len(clean) >= 11:
                        return clean[1:]
                return clean

            normalized_incoming = normalize_phone(phone_number)

            # Buscar empleados con teléfono
            employees = self.env['hr.employee'].sudo().search([
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

                # Verificar últimos 9 dígitos
                if len(normalized_incoming) >= 9:
                    local_incoming = normalized_incoming[-9:]
                    if len(mobile_normalized) >= 9 and local_incoming == mobile_normalized[-9:]:
                        return employee
                    if len(work_normalized) >= 9 and local_incoming == work_normalized[-9:]:
                        return employee

            return None

        except Exception as e:
            _logger.error(f"Error buscando empleado por teléfono: {e}")
            return None

    def _validate_attendance_state(self, employee, attendance_type):
        """
        Valida si el empleado puede registrar el tipo de asistencia solicitado
        """
        try:
            if attendance_type == 'check_in':
                # Verificar que no tenga entrada activa sin salida
                open_attendance = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if open_attendance:
                    check_in_date = open_attendance.check_in.strftime('%d/%m/%Y %H:%M')
                    return {
                        'valid': False,
                        'message': f"Ya tienes una entrada registrada desde el {check_in_date}. Debes registrar salida primero."
                    }

                return {'valid': True, 'message': 'Entrada autorizada'}

            elif attendance_type == 'check_out':
                # Buscar entrada sin salida
                open_attendance = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if not open_attendance:
                    return {
                        'valid': False,
                        'message': "No tienes ninguna entrada registrada pendiente de salida."
                    }

                return {
                    'valid': True,
                    'message': 'Salida autorizada',
                    'open_attendance': open_attendance
                }

            return {'valid': False, 'message': 'Tipo de asistencia no válido'}

        except Exception as e:
            _logger.error(f"Error validando estado de asistencia: {e}")
            return {'valid': False, 'message': 'Error interno al validar asistencia'}

    def _register_attendance(self, employee, attendance_type, validation_result=None, location_data=None):
        """
        Registra la asistencia del empleado
        """
        try:
            if attendance_type == 'check_in':
                if employee.attendance_state == 'checked_in':
                    return False

                attendance = employee.sudo()._attendance_action_change()

                if location_data:
                    self._add_location_to_attendance(attendance, location_data, employee)

                return attendance

            elif attendance_type == 'check_out':
                if validation_result and 'open_attendance' in validation_result:
                    open_attendance = validation_result['open_attendance']
                else:
                    open_attendance = self.env['hr.attendance'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('check_out', '=', False)
                    ], limit=1, order='check_in desc')

                if not open_attendance:
                    return False

                open_attendance.sudo().write({
                    'check_out': datetime.now()
                })

                if location_data:
                    self._add_location_to_attendance(open_attendance, location_data, employee)

                return open_attendance

            return False

        except Exception as e:
            _logger.error(f"Error registrando asistencia: {e}")
            return False

    def _add_location_to_attendance(self, attendance, location_data, employee):
        """
        Añade datos de ubicación a un registro de asistencia
        """
        try:
            address = self._get_address_from_coordinates(
                location_data.get('latitude'),
                location_data.get('longitude')
            )

            attendance.sudo().write({
                'whatsapp_latitude': location_data.get('latitude'),
                'whatsapp_longitude': location_data.get('longitude'),
                'whatsapp_location_address': address or location_data.get('address', ''),
                'whatsapp_location_accuracy': location_data.get('accuracy', 0.0)
            })

            employee.sudo().write({
                'last_whatsapp_latitude': location_data.get('latitude'),
                'last_whatsapp_longitude': location_data.get('longitude'),
                'last_whatsapp_location_time': datetime.now(),
                'last_whatsapp_address': address or location_data.get('address', '')
            })

        except Exception as e:
            _logger.error(f"Error añadiendo ubicación al registro: {e}")

    def _get_address_from_coordinates(self, latitude, longitude):
        """
        Obtiene dirección aproximada desde coordenadas
        """
        if latitude and longitude:
            return f"Ubicación: {latitude:.6f}, {longitude:.6f}"
        return None

    def _request_location_for_attendance(self, chat, phone_number, employee, attendance_type, validation_result=None):
        """
        Solicita la ubicación al empleado antes de registrar asistencia
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Guardar solicitud pendiente
            self.env['ir.config_parameter'].sudo().set_param(
                f'whatsapp_attendance_pending_{phone_number}',
                f'{employee.id}|{attendance_type}'
            )

            message = f"📍 Hola {employee.name}!\n\nPara registrar tu {action_text}, por favor envía tu ubicación:\n\n1️⃣ Toca el botón 📎 (clip)\n2️⃣ Selecciona *Ubicación*\n3️⃣ Elige *Ubicación actual*\n4️⃣ Envía tu ubicación\n\n⏰ Tienes 2 minutos para enviarla."

            self._send_message_to_channel(chat, message)

        except Exception as e:
            _logger.error(f"Error solicitando ubicación: {e}")
            # Si hay error, registrar sin ubicación
            attendance_result = self._register_attendance(employee, attendance_type, validation_result)
            if attendance_result:
                self._send_confirmation_response(chat, attendance_type, employee)

    def _process_location_response(self, chat, phone_number, message):
        """
        Procesa la respuesta de ubicación del empleado
        """
        try:
            pending_key = f'whatsapp_attendance_pending_{phone_number}'
            pending_data = self.env['ir.config_parameter'].sudo().get_param(pending_key)

            if not pending_data:
                return False

            # Parsear datos pendientes
            parts = pending_data.split('|')
            employee_id = int(parts[0])
            attendance_type = parts[1]

            employee = self.env['hr.employee'].sudo().browse(employee_id)

            if not employee.exists():
                return False

            # Extraer datos de ubicación
            location_data = {
                'latitude': message.get('location', {}).get('latitude'),
                'longitude': message.get('location', {}).get('longitude'),
                'name': message.get('location', {}).get('name', ''),
                'address': message.get('location', {}).get('address', '')
            }

            # Limpiar solicitud pendiente
            self.env['ir.config_parameter'].sudo().set_param(pending_key, False)

            # Validar estado de asistencia
            validation_result = self._validate_attendance_state(employee, attendance_type)
            if not validation_result['valid']:
                self._send_error_response(chat, validation_result['message'])
                return True

            # Registrar asistencia con ubicación
            attendance_result = self._register_attendance(
                employee, attendance_type, validation_result, location_data
            )

            if attendance_result:
                self._send_confirmation_response_with_location(chat, attendance_type, employee, location_data)
            else:
                self._send_error_response(chat, "Error al registrar asistencia")

            return True

        except Exception as e:
            _logger.error(f"Error procesando ubicación: {e}")
            return False

    def _send_confirmation_response(self, chat, attendance_type, employee):
        """
        Envía mensaje de confirmación al empleado
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Obtener hora en zona horaria local
            user_tz = self.env.user.tz or 'Europe/Madrid'
            local_tz = pytz.timezone(user_tz)
            now_local = datetime.now(local_tz)
            attendance_time = now_local.strftime("%H:%M")
            date_now = now_local.strftime("%d/%m/%Y")

            # Obtener mensaje de configuración
            response_config = self.env['attendance.keyword.config'].sudo().get_response_config(attendance_type)

            if response_config and response_config.custom_message:
                message = response_config.get_response_message(employee.name, attendance_time, date_now, action_text)
            else:
                message = f"✅ Hola {employee.name},\n\nTu *{action_text}* ha sido registrada correctamente.\n\n🕐 Hora: {attendance_time}\n📅 Fecha: {date_now}\n\n¡Que tengas un buen día!"

            self._send_message_to_channel(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando confirmación: {e}")

    def _send_confirmation_response_with_location(self, chat, attendance_type, employee, location_data):
        """
        Envía mensaje de confirmación incluyendo información de ubicación
        """
        try:
            # Primero enviar confirmación normal
            self._send_confirmation_response(chat, attendance_type, employee)

            # Luego enviar información de ubicación
            lat = location_data.get('latitude')
            lng = location_data.get('longitude')

            if lat and lng:
                location_message = f"📍 *Ubicación registrada:*\n\n🗺️ Coordenadas: {lat:.6f}, {lng:.6f}\n\n📍 Ver en Google Maps: https://maps.google.com/?q={lat},{lng}"
                self._send_message_to_channel(chat, location_message)

        except Exception as e:
            _logger.error(f"Error enviando confirmación con ubicación: {e}")

    def _send_error_response(self, chat, error_message):
        """
        Envía mensaje de error al empleado
        """
        try:
            message = f"❌ *Error de Asistencia*\n\n{error_message}\n\nPor favor, contacta con Recursos Humanos si el problema persiste."
            self._send_message_to_channel(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando mensaje de error: {e}")

    def _send_message_to_channel(self, chat, message):
        """
        Envía un mensaje al canal del gateway
        """
        try:
            # Usar el método message_post del canal
            chat.sudo().message_post(
                body=message,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        except Exception as e:
            _logger.error(f"Error enviando mensaje al canal: {e}")


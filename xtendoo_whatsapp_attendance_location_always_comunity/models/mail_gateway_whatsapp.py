# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import re
from datetime import datetime

import pytz

from odoo import _, models

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappAttendanceLocationAlways(models.AbstractModel):
    """
    Hereda del servicio de WhatsApp Gateway para gestionar asistencia con ubicación obligatoria
    Este módulo es completamente independiente y no requiere xtendoo_whatsapp_attendance_comunity
    """
    _inherit = "mail.gateway.whatsapp"

    def _process_update(self, chat, message, value):
        """
        Override del método _process_update para interceptar mensajes de asistencia
        antes del procesamiento normal
        """
        # Verificar si es un mensaje de asistencia
        if self._is_attendance_message_location_always(message):
            attendance_processed = self._handle_attendance_message_location_always(chat, message, value)
            if attendance_processed:
                # Si fue procesado como asistencia, no continuar con el procesamiento normal
                return

        # Si no es mensaje de asistencia o no se pudo procesar, continuar normalmente
        return super()._process_update(chat, message, value)

    def _is_attendance_message_location_always(self, message):
        """
        Verifica si el mensaje es un comando de asistencia
        """
        if message.get('type') not in ['text', 'location']:
            return False

        if message.get('type') == 'location':
            # Verificar si hay una solicitud de ubicación pendiente
            phone_number = message.get('from', '')
            pending_key = f'whatsapp_attendance_location_always_pending_{phone_number}'
            pending_data = self.env['ir.config_parameter'].sudo().get_param(pending_key)
            return bool(pending_data)

        if message.get('type') == 'text':
            text_content = message.get('text', {}).get('body', '').strip().lower()
            # Verificar si es comando de consulta de asistencias
            if self._is_attendance_query_command(text_content):
                return True
            attendance_type = self._detect_attendance_command_location_always(text_content)
            return attendance_type is not None

        return False

    def _is_attendance_query_command(self, text):
        """
        Verifica si el texto es un comando de consulta de asistencias
        """
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Obtener palabras clave de consulta desde configuración
        query_keywords = self.env['attendance.keyword.config.location.always'].sudo().get_active_keywords('query')

        # Si no hay configuración, usar palabras clave por defecto
        if not query_keywords:
            query_keywords = ['/asistencia', '/asistencias', '/mis asistencias', '/historial', '/horas']

        for keyword in query_keywords:
            keyword_lower = keyword.lower()
            if self._keyword_matches_location_always(keyword_lower, normalized_text):
                return True
        return False

    def _detect_attendance_command_location_always(self, text):
        """
        Detecta si el texto contiene un comando de asistencia válido
        Retorna 'check_in', 'check_out' o None
        """
        # Normalizar texto
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Obtener palabras clave de entrada desde configuración
        entrada_keywords = self.env['attendance.keyword.config.location.always'].sudo().get_active_keywords('check_in')
        salida_keywords = self.env['attendance.keyword.config.location.always'].sudo().get_active_keywords('check_out')

        _logger.debug(f"Palabras clave entrada: {entrada_keywords}")
        _logger.debug(f"Palabras clave salida: {salida_keywords}")

        # Buscar patrones de entrada
        for keyword in entrada_keywords:
            keyword_lower = keyword.lower()
            if self._keyword_matches_location_always(keyword_lower, normalized_text):
                _logger.info(f"Comando de ENTRADA detectado: '{keyword}'")
                return 'check_in'

        # Buscar patrones de salida
        for keyword in salida_keywords:
            keyword_lower = keyword.lower()
            if self._keyword_matches_location_always(keyword_lower, normalized_text):
                _logger.info(f"Comando de SALIDA detectado: '{keyword}'")
                return 'check_out'

        return None

    def _keyword_matches_location_always(self, keyword, text):
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

    def _handle_attendance_message_location_always(self, chat, message, value):
        """
        Maneja un mensaje de asistencia - SIEMPRE solicita ubicación
        """
        try:
            phone_number = message.get('from', '')

            # Si es un mensaje de ubicación, procesarlo
            if message.get('type') == 'location':
                return self._process_location_response_location_always(chat, phone_number, message)

            # Procesar mensaje de texto
            text_content = message.get('text', {}).get('body', '').strip().lower()

            # Verificar si es comando de consulta de asistencias
            if self._is_attendance_query_command(text_content):
                return self._handle_attendance_query(chat, phone_number)

            attendance_type = self._detect_attendance_command_location_always(text_content)

            if not attendance_type:
                return False

            # Buscar empleado por teléfono del partner del canal
            employee = self._find_employee_by_channel_location_always(chat)

            if not employee:
                # Intentar buscar por número de teléfono
                employee = self._find_employee_by_phone_location_always(phone_number)

            if not employee:
                _logger.warning(f"No se encontró empleado para el teléfono: {phone_number}")
                self._send_error_response_location_always(chat, "No se encontró empleado asociado a este número")
                return True

            _logger.info(f"Empleado encontrado: {employee.name} (ID: {employee.id})")

            # Validar estado de asistencia
            validation_result = self._validate_attendance_state_location_always(employee, attendance_type)
            if not validation_result['valid']:
                _logger.warning(f"Validación fallida: {validation_result['message']}")
                self._send_error_response_location_always(chat, validation_result['message'])
                return True

            # SIEMPRE registrar la asistencia primero y luego pedir ubicación
            attendance_result = self._register_attendance_location_always(employee, attendance_type, validation_result)

            if attendance_result:
                _logger.info(f"Asistencia registrada para {employee.name}, solicitando ubicación...")
                # Enviar confirmación
                self._send_confirmation_response_location_always(chat, attendance_type, employee)

                # Guardar información para procesar la ubicación después
                self.env['ir.config_parameter'].sudo().set_param(
                    f'whatsapp_attendance_location_always_pending_{phone_number}',
                    f'{employee.id}|{attendance_type}|{attendance_result.id}'
                )

                # Solicitar ubicación
                self._request_location_always(chat, employee, attendance_type)
            else:
                self._send_error_response_location_always(chat, "Error al registrar asistencia")

            return True

        except Exception as e:
            _logger.error(f"Error manejando mensaje de asistencia: {e}")
            return False

    def _find_employee_by_channel_location_always(self, chat):
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
                    employee = self._find_employee_by_phone_location_always(partner.mobile)
                if not employee and partner.phone:
                    employee = self._find_employee_by_phone_location_always(partner.phone)

            return employee

        except Exception as e:
            _logger.error(f"Error buscando empleado por canal: {e}")
            return None

    def _find_employee_by_phone_location_always(self, phone_number):
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

    def _validate_attendance_state_location_always(self, employee, attendance_type):
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

    def _register_attendance_location_always(self, employee, attendance_type, validation_result=None):
        """
        Registra la asistencia sin esperar ubicación
        """
        try:
            if attendance_type == 'check_in':
                if employee.attendance_state == 'checked_in':
                    return False

                attendance = employee.sudo()._attendance_action_change()
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

                return open_attendance

            return False

        except Exception as e:
            _logger.error(f"Error registrando asistencia: {e}")
            return False

    def _request_location_always(self, chat, employee, attendance_type):
        """
        Solicita la ubicación automáticamente después de registrar la asistencia
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Obtener mensaje de configuración
            response_config = self.env['attendance.keyword.config.location.always'].sudo().get_response_config(attendance_type)

            if response_config:
                message = response_config.get_location_request_message(employee.name, action_text)
            else:
                message = f"📍 Tu {action_text} ya está registrada ✅\n\nAhora puedes enviar tu ubicación para completar el registro.\n\n*Instrucciones:*\n1️⃣ Toca el botón 📎 (clip)\n2️⃣ Selecciona *Ubicación*\n3️⃣ Elige *Ubicación actual*\n4️⃣ Envía tu ubicación\n\n⏰ Tienes 3 minutos para enviarla."

            self._send_message_to_channel_location_always(chat, message)

        except Exception as e:
            _logger.error(f"Error solicitando ubicación: {e}")

    def _process_location_response_location_always(self, chat, phone_number, message):
        """
        Procesa la respuesta de ubicación y la añade al registro de asistencia existente
        """
        try:
            pending_key = f'whatsapp_attendance_location_always_pending_{phone_number}'
            pending_data = self.env['ir.config_parameter'].sudo().get_param(pending_key)

            if not pending_data:
                return False

            # Parsear datos pendientes
            parts = pending_data.split('|')
            employee_id = int(parts[0])
            attendance_type = parts[1]
            attendance_id = int(parts[2]) if len(parts) > 2 else None

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

            if attendance_id:
                # Añadir ubicación a la asistencia existente
                attendance = self.env['hr.attendance'].sudo().browse(attendance_id)
                if attendance.exists():
                    self._add_location_to_attendance_location_always(attendance, location_data, attendance_type, employee)
                    self._send_location_confirmation_location_always(chat, location_data, employee, attendance_type)
                    return True

            return False

        except Exception as e:
            _logger.error(f"Error procesando ubicación: {e}")
            return False

    def _add_location_to_attendance_location_always(self, attendance, location_data, attendance_type, employee):
        """
        Añade datos de ubicación a un registro de asistencia existente
        Usa campos separados para entrada y salida
        """
        try:
            address = self._get_address_from_coordinates_location_always(
                location_data.get('latitude'),
                location_data.get('longitude')
            )

            if attendance_type == 'check_in':
                attendance.sudo().write({
                    'whatsapp_check_in_latitude': location_data.get('latitude'),
                    'whatsapp_check_in_longitude': location_data.get('longitude'),
                    'whatsapp_check_in_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_in_location_accuracy': location_data.get('accuracy', 0.0),
                })
            else:  # check_out
                attendance.sudo().write({
                    'whatsapp_check_out_latitude': location_data.get('latitude'),
                    'whatsapp_check_out_longitude': location_data.get('longitude'),
                    'whatsapp_check_out_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_out_location_accuracy': location_data.get('accuracy', 0.0)
                })

            # Actualizar última ubicación del empleado
            employee.sudo().write({
                'last_whatsapp_latitude': location_data.get('latitude'),
                'last_whatsapp_longitude': location_data.get('longitude'),
                'last_whatsapp_location_time': datetime.now(),
                'last_whatsapp_address': address or location_data.get('address', '')
            })

            _logger.info(f"Ubicación añadida al registro {attendance.id} para {attendance_type}")

        except Exception as e:
            _logger.error(f"Error añadiendo ubicación al registro: {e}")

    def _get_address_from_coordinates_location_always(self, latitude, longitude):
        """
        Obtiene dirección aproximada desde coordenadas
        """
        if latitude and longitude:
            return f"Ubicación: {latitude:.6f}, {longitude:.6f}"
        return None

    def _send_confirmation_response_location_always(self, chat, attendance_type, employee):
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
            response_config = self.env['attendance.keyword.config.location.always'].sudo().get_response_config(attendance_type)

            if response_config and response_config.custom_message:
                message = response_config.get_response_message(employee.name, attendance_time, date_now, action_text)
            else:
                message = f"✅ Hola {employee.name},\n\nTu *{action_text}* ha sido registrada correctamente.\n\n🕐 Hora: {attendance_time}\n📅 Fecha: {date_now}\n\n¡Que tengas un buen día!"

            self._send_message_to_channel_location_always(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando confirmación: {e}")

    def _send_location_confirmation_location_always(self, chat, location_data, employee, attendance_type):
        """
        Envía confirmación de que la ubicación ha sido añadida
        """
        try:
            lat = location_data.get('latitude')
            lng = location_data.get('longitude')

            if lat and lng:
                # Obtener mensaje de configuración
                response_config = self.env['attendance.keyword.config.location.always'].sudo().get_response_config(attendance_type)

                if response_config:
                    message = response_config.get_location_received_message(employee.name, lat, lng)
                else:
                    message = f"🎉 *¡Ubicación añadida exitosamente!*\n\n📍 Coordenadas: {lat:.6f}, {lng:.6f}\n\n🗺️ Ver en Google Maps: https://maps.google.com/?q={lat},{lng}\n\n✅ Registro completado"

                self._send_message_to_channel_location_always(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando confirmación de ubicación: {e}")

    def _send_error_response_location_always(self, chat, error_message):
        """
        Envía mensaje de error al empleado
        """
        try:
            message = f"❌ *Error de Asistencia*\n\n{error_message}\n\nPor favor, contacta con Recursos Humanos si el problema persiste."
            self._send_message_to_channel_location_always(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando mensaje de error: {e}")

    def _send_message_to_channel_location_always(self, chat, message):
        """
        Envía un mensaje al canal del gateway.
        Importante: Quitamos el contexto no_gateway_notification para que el mensaje
        se envíe realmente a WhatsApp.
        """
        try:
            # Quitar el contexto no_gateway_notification para que el mensaje se envíe a WhatsApp
            chat_without_context = chat.sudo().with_context(no_gateway_notification=False)
            chat_without_context.message_post(
                body=message,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        except Exception as e:
            _logger.error(f"Error enviando mensaje al canal: {e}")

    def _handle_attendance_query(self, chat, phone_number):
        """
        Maneja el comando de consulta de asistencias del empleado
        """
        try:
            # Buscar empleado
            employee = self._find_employee_by_channel_location_always(chat)
            if not employee:
                employee = self._find_employee_by_phone_location_always(phone_number)

            if not employee:
                _logger.warning(f"No se encontró empleado para el teléfono: {phone_number}")
                self._send_error_response_location_always(chat, "No se encontró empleado asociado a este número")
                return True

            # Obtener zona horaria
            user_tz = self.env.user.tz or 'Europe/Madrid'
            local_tz = pytz.timezone(user_tz)

            # Obtener asistencias del mes actual
            now = datetime.now(local_tz)
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            attendances = self.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', first_day_of_month.strftime('%Y-%m-%d 00:00:00'))
            ], order='check_in desc', limit=10)

            # Generar mensaje de resumen
            message = self._generate_attendance_summary(employee, attendances, now, local_tz)

            self._send_message_to_channel_location_always(chat, message)
            return True

        except Exception as e:
            _logger.error(f"Error manejando consulta de asistencias: {e}")
            self._send_error_response_location_always(chat, "Error al consultar asistencias")
            return True

    def _generate_attendance_summary(self, employee, attendances, now, local_tz):
        """
        Genera el mensaje de resumen de asistencias
        """
        month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }

        current_month = month_names.get(now.month, '')

        # Calcular horas totales del mes
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', first_day_of_month.strftime('%Y-%m-%d 00:00:00'))
        ])

        total_hours = sum(att.worked_hours or 0 for att in month_attendances)
        total_hours_int = int(total_hours)
        total_minutes = int((total_hours - total_hours_int) * 60)

        # Estado actual
        current_state = "🟢 Trabajando" if employee.attendance_state == 'checked_in' else "🔴 Fuera"

        # Construir mensaje
        message = f"📊 *Resumen de Asistencias*\n"
        message += f"👤 {employee.name}\n"
        message += f"📅 {current_month} {now.year}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        message += f"*Estado actual:* {current_state}\n"
        message += f"*Horas trabajadas este mes:* {total_hours_int}h {total_minutes}m\n\n"

        if attendances:
            message += f"📋 *Últimos registros:*\n\n"

            for att in attendances[:7]:  # Mostrar máximo 7 registros
                check_in_local = att.check_in.astimezone(local_tz) if att.check_in else None
                check_out_local = att.check_out.astimezone(local_tz) if att.check_out else None

                date_str = check_in_local.strftime('%d/%m') if check_in_local else '-'
                check_in_str = check_in_local.strftime('%H:%M') if check_in_local else '-'
                check_out_str = check_out_local.strftime('%H:%M') if check_out_local else '⏳'

                worked = att.worked_hours or 0
                worked_hours = int(worked)
                worked_mins = int((worked - worked_hours) * 60)
                worked_str = f"{worked_hours}h{worked_mins}m" if att.check_out else "-"

                message += f"• {date_str}: {check_in_str} → {check_out_str} ({worked_str}) {has_location}\n"

            if len(attendances) > 7:
                message += f"\n_... y {len(month_attendances) - 7} registros más_\n"
        else:
            message += "📋 No hay registros de asistencia este mes.\n"


        return message



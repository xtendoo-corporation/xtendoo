# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from datetime import datetime

import pytz

from odoo import models

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappAttendanceLocationAlways(models.AbstractModel):
    """
    Hereda del servicio de WhatsApp Gateway para SIEMPRE solicitar ubicación
    sin preguntar al usuario
    """
    _inherit = "mail.gateway.whatsapp"

    def _handle_attendance_message(self, chat, message, value):
        """
        Override del método para SIEMPRE solicitar ubicación automáticamente
        sin preguntar al usuario
        """
        try:
            phone_number = message.get('from', '')

            # Si es un mensaje de ubicación, procesarlo
            if message.get('type') == 'location':
                return self._process_location_response_always(chat, phone_number, message)

            # Procesar mensaje de texto
            text_content = message.get('text', {}).get('body', '').strip().lower()
            attendance_type = self._detect_attendance_command(text_content)

            if not attendance_type:
                return False

            # Buscar empleado
            employee = self._find_employee_by_channel(chat)
            if not employee:
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

            # SIEMPRE registrar la asistencia primero y luego pedir ubicación
            attendance_result = self._register_attendance_always(employee, attendance_type, validation_result)

            if attendance_result:
                _logger.info(f"Asistencia registrada para {employee.name}, solicitando ubicación...")
                # Enviar confirmación
                self._send_confirmation_response(chat, attendance_type, employee)

                # Guardar información para procesar la ubicación después
                self.env['ir.config_parameter'].sudo().set_param(
                    f'whatsapp_attendance_pending_{phone_number}',
                    f'{employee.id}|{attendance_type}|{attendance_result.id}'
                )

                # Solicitar ubicación
                self._request_location_always(chat, employee, attendance_type)
            else:
                self._send_error_response(chat, "Error al registrar asistencia")

            return True

        except Exception as e:
            _logger.error(f"Error manejando mensaje de asistencia: {e}")
            return False

    def _register_attendance_always(self, employee, attendance_type, validation_result=None):
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

            message = f"📍 Tu {action_text} ya está registrada ✅\n\nAhora puedes enviar tu ubicación para completar el registro.\n\n*Instrucciones:*\n1️⃣ Toca el botón 📎 (clip)\n2️⃣ Selecciona *Ubicación*\n3️⃣ Elige *Ubicación actual*\n4️⃣ Envía tu ubicación\n\n⏰ Tienes 3 minutos para enviarla."

            self._send_message_to_channel(chat, message)

        except Exception as e:
            _logger.error(f"Error solicitando ubicación: {e}")

    def _process_location_response_always(self, chat, phone_number, message):
        """
        Procesa la respuesta de ubicación y la añade al registro de asistencia existente
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
                    self._add_location_to_attendance_always(attendance, location_data, attendance_type, employee)
                    self._send_location_confirmation(chat, location_data)
                    return True

            return False

        except Exception as e:
            _logger.error(f"Error procesando ubicación: {e}")
            return False

    def _add_location_to_attendance_always(self, attendance, location_data, attendance_type, employee):
        """
        Añade datos de ubicación a un registro de asistencia existente
        Usa campos separados para entrada y salida
        """
        try:
            address = self._get_address_from_coordinates(
                location_data.get('latitude'),
                location_data.get('longitude')
            )

            if attendance_type == 'check_in':
                attendance.sudo().write({
                    'whatsapp_check_in_latitude': location_data.get('latitude'),
                    'whatsapp_check_in_longitude': location_data.get('longitude'),
                    'whatsapp_check_in_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_in_location_accuracy': location_data.get('accuracy', 0.0),
                    # También actualizar campos heredados del módulo base
                    'whatsapp_latitude': location_data.get('latitude'),
                    'whatsapp_longitude': location_data.get('longitude'),
                    'whatsapp_location_address': address or location_data.get('address', ''),
                    'whatsapp_location_accuracy': location_data.get('accuracy', 0.0)
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

    def _send_location_confirmation(self, chat, location_data):
        """
        Envía confirmación de que la ubicación ha sido añadida
        """
        try:
            lat = location_data.get('latitude')
            lng = location_data.get('longitude')

            if lat and lng:
                message = f"🎉 *¡Ubicación añadida exitosamente!*\n\n📍 Coordenadas: {lat:.6f}, {lng:.6f}\n\n🗺️ Ver en Google Maps: https://maps.google.com/?q={lat},{lng}\n\n✅ Registro completado"
                self._send_message_to_channel(chat, message)

        except Exception as e:
            _logger.error(f"Error enviando confirmación de ubicación: {e}")


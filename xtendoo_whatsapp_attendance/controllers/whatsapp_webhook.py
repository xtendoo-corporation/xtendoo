import logging
import json
import re
from datetime import datetime
from http import HTTPStatus
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.whatsapp.controller.main import Webhook

_logger = logging.getLogger(__name__)


class WhatsAppAttendanceWebhook(Webhook):
    """
    Controlador que hereda de Webhook para mostrar información detallada
    de las peticiones recibidas en el webhook de WhatsApp y gestionar asistencia automática
    """

    @http.route('/whatsapp/webhook/', methods=['POST'], type="json", auth="public")
    def webhookpost(self):
        """
        Método heredado que procesa mensajes de WhatsApp y gestiona asistencia automática.
        ESTE ES EL MÉTODO QUE RECIBE LOS MENSAJES REALES DE TU MÓVIL.
        """
        print("="*80)
        print("🔥 XTENDOO WHATSAPP ATTENDANCE - MENSAJE RECIBIDO (POST)")
        print("="*80)

        # Obtener datos de la petición
        raw_data = request.httprequest.data
        data = json.loads(raw_data)

        print(f"Método HTTP: {request.httprequest.method}")
        print(f"URL completa: {request.httprequest.url}")
        print(f"Content-Type: {request.httprequest.content_type}")

        # Mostrar headers importantes
        print("\n--- HEADERS IMPORTANTES ---")
        important_headers = ['X-Hub-Signature-256', 'User-Agent', 'Content-Length']
        for header in important_headers:
            value = request.httprequest.headers.get(header)
            if value:
                print(f"{header}: {value}")

        # Mostrar datos RAW recibidos
        print(f"\n--- DATOS RAW RECIBIDOS ---")
        print(f"Tamaño: {len(raw_data)} bytes")
        print(f"Datos: {raw_data.decode('utf-8')}")

        # Mostrar datos JSON parseados
        print(f"\n--- DATOS JSON PARSEADOS ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Procesar mensajes para asistencia automática
        self._process_attendance_messages(data)

        # Analizar estructura del webhook
        print(f"\n--- ANÁLISIS DE LA ESTRUCTURA ---")
        if 'entry' in data:
            print(f"Número de entradas: {len(data['entry'])}")

            for i, entry in enumerate(data['entry']):
                print(f"\n  ENTRADA {i+1}:")
                print(f"    Account ID: {entry.get('id')}")
                print(f"    Time: {entry.get('time')}")

                if 'changes' in entry:
                    print(f"    Número de cambios: {len(entry['changes'])}")

                    for j, change in enumerate(entry['changes']):
                        print(f"\n    CAMBIO {j+1}:")
                        print(f"      Field: {change.get('field')}")

                        if 'value' in change:
                            value = change['value']
                            print(f"      Value keys: {list(value.keys())}")

                            # Si hay mensajes
                            if 'messages' in value:
                                print(f"\n      📱 MENSAJES ENCONTRADOS:")
                                for k, message in enumerate(value['messages']):
                                    print(f"        MENSAJE {k+1}:")
                                    print(f"          ID: {message.get('id')}")
                                    print(f"          From: {message.get('from')}")
                                    print(f"          Timestamp: {message.get('timestamp')}")
                                    print(f"          Type: {message.get('type')}")

                                    # Contenido del mensaje según tipo
                                    if message.get('type') == 'text':
                                        text_content = message.get('text', {}).get('body', '')
                                        print(f"          📝 TEXTO: '{text_content}'")
                                    elif message.get('type') == 'image':
                                        print(f"          🖼️ IMAGEN: {message.get('image', {})}")
                                    elif message.get('type') == 'audio':
                                        print(f"          🎵 AUDIO: {message.get('audio', {})}")
                                    elif message.get('type') == 'document':
                                        print(f"          📄 DOCUMENTO: {message.get('document', {})}")

                            # Si hay contactos
                            if 'contacts' in value:
                                print(f"\n      👥 CONTACTOS:")
                                for contact in value['contacts']:
                                    print(f"        Nombre: {contact.get('profile', {}).get('name')}")
                                    print(f"        WhatsApp ID: {contact.get('wa_id')}")

                            # Si hay estados de mensaje
                            if 'statuses' in value:
                                print(f"\n      📊 ESTADOS DE MENSAJE:")
                                for status in value['statuses']:
                                    print(f"        ID: {status.get('id')}")
                                    print(f"        Status: {status.get('status')}")
                                    print(f"        Timestamp: {status.get('timestamp')}")
                                    print(f"        Recipient: {status.get('recipient_id')}")

        print(f"\n--- PROCESAMIENTO ORIGINAL ---")
        print("Llamando al método original...")

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

    def _process_attendance_messages(self, data):
        """
        Procesa los mensajes de WhatsApp para detectar comandos de asistencia
        y registrar entrada/salida automáticamente
        """
        print("\n🏢 --- PROCESAMIENTO DE ASISTENCIA AUTOMÁTICA ---")

        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})

                        # Procesar mensajes recibidos
                        for message in value.get('messages', []):
                            if message.get('type') == 'text':
                                self._handle_attendance_message(message, value)

        except Exception as e:
            print(f"❌ Error procesando asistencia: {e}")
            _logger.error("Error en procesamiento de asistencia: %s", e)

    def _handle_attendance_message(self, message, value):
        """
        Maneja un mensaje de texto individual para detectar comandos de asistencia
        """
        try:
            # Extraer información del mensaje
            phone_number = message.get('from', '')
            text_content = message.get('text', {}).get('body', '').strip().lower()
            message_id = message.get('id', '')
            timestamp = message.get('timestamp', '')

            print(f"\n📋 Procesando mensaje de asistencia:")
            print(f"   Teléfono: {phone_number}")
            print(f"   Texto: '{text_content}'")
            print(f"   ID Mensaje: {message_id}")
            print(f"   Timestamp: {timestamp}")

            # Detectar comando de asistencia
            attendance_type = self._detect_attendance_command(text_content)

            if attendance_type:
                print(f"✅ Comando detectado: {attendance_type}")

                # Buscar empleado por número de teléfono
                employee = self._find_employee_by_phone(phone_number)

                if employee:
                    print(f"👤 Empleado encontrado: {employee.name} (ID: {employee.id})")

                    # Registrar asistencia
                    attendance_result = self._register_attendance(employee, attendance_type)

                    if attendance_result:
                        print(f"✅ Asistencia registrada exitosamente")
                        # Aquí podrías enviar un mensaje de confirmación de vuelta
                        self._send_confirmation_message(phone_number, attendance_type, employee)
                    else:
                        print(f"❌ Error al registrar asistencia")
                        self._send_error_message(phone_number, "Error al registrar asistencia")
                else:
                    print(f"❌ No se encontró empleado con el teléfono: {phone_number}")
                    self._send_error_message(phone_number, "No se encontró empleado asociado a este número")
            else:
                print(f"ℹ️ Mensaje no es comando de asistencia: '{text_content}'")

        except Exception as e:
            print(f"❌ Error manejando mensaje de asistencia: {e}")
            _logger.error("Error manejando mensaje de asistencia: %s", e)

    def _detect_attendance_command(self, text):
        """
        Detecta si el texto contiene un comando de asistencia válido
        Retorna 'check_in', 'check_out' o None
        """
        # Normalizar texto (quitar acentos, espacios extra, etc.)
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Patrones para entrada
        entrada_patterns = [
            r'\bentrada\b', r'\bentrar\b', r'\bllegar\b', r'\bllego\b',
            r'\bcheck\s*in\b', r'\bfichar\s*entrada\b', r'\binicio\b',
            r'\bcomenzar\b', r'\bempezar\b'
        ]

        # Patrones para salida
        salida_patterns = [
            r'\bsalida\b', r'\bsalir\b', r'\bmarchar\b', r'\bme\s*voy\b',
            r'\bcheck\s*out\b', r'\bfichar\s*salida\b', r'\bfin\b',
            r'\bterminar\b', r'\bacabar\b', r'\bfinalizar\b'
        ]

        # Buscar patrones de entrada
        for pattern in entrada_patterns:
            if re.search(pattern, normalized_text):
                return 'check_in'

        # Buscar patrones de salida
        for pattern in salida_patterns:
            if re.search(pattern, normalized_text):
                return 'check_out'

        return None

    def _find_employee_by_phone(self, phone_number):
        """
        Busca un empleado por su número de teléfono/WhatsApp
        Normaliza los números para eliminar códigos de país, espacios y caracteres especiales
        """
        try:
            # Función auxiliar para normalizar números de teléfono
            def normalize_phone(phone):
                if not phone:
                    return ""
                # Quitar todo excepto números
                clean = re.sub(r'[^\d]', '', str(phone))
                # Si empieza con código de país común, quitarlo
                # España: 34, México: 52, Argentina: 54, Colombia: 57, etc.
                if len(clean) > 9:
                    # Códigos de país comunes de 2 dígitos
                    country_codes_2 = ['34', '52', '54', '57', '58', '51', '56', '55', '33', '49', '44', '39']
                    # Códigos de país de 1 dígito (como +1 USA/Canadá)
                    country_codes_1 = ['1']

                    for code in country_codes_2:
                        if clean.startswith(code) and len(clean) >= len(code) + 9:
                            return clean[len(code):]

                    for code in country_codes_1:
                        if clean.startswith(code) and len(clean) >= len(code) + 10:
                            return clean[len(code):]

                return clean

            # Normalizar el número recibido del webhook
            normalized_incoming = normalize_phone(phone_number)

            print(f"🔍 Buscando empleado con teléfono:")
            print(f"   Original: {phone_number}")
            print(f"   Normalizado: {normalized_incoming}")

            # Buscar todos los empleados que tengan teléfono
            employees = request.env['hr.employee'].sudo().search([
                '|',
                ('mobile_phone', '!=', False),
                ('work_phone', '!=', False)
            ])

            print(f"📱 Empleados con teléfono: {len(employees)}")

            # Buscar coincidencia normalizando cada número de empleado
            for employee in employees:
                # Normalizar números del empleado
                mobile_normalized = normalize_phone(employee.mobile_phone)
                work_normalized = normalize_phone(employee.work_phone)

                print(f"👤 Comparando con {employee.name}:")
                print(f"   Mobile original: {employee.mobile_phone} → normalizado: {mobile_normalized}")
                print(f"   Work original: {employee.work_phone} → normalizado: {work_normalized}")

                # Verificar coincidencias exactas
                if (normalized_incoming and
                    (normalized_incoming == mobile_normalized or
                     normalized_incoming == work_normalized)):

                    print(f"✅ ¡COINCIDENCIA ENCONTRADA! Empleado: {employee.name}")
                    return employee

                # También verificar los últimos 9 dígitos (número local)
                if len(normalized_incoming) >= 9:
                    local_incoming = normalized_incoming[-9:]

                    if len(mobile_normalized) >= 9 and local_incoming == mobile_normalized[-9:]:
                        print(f"✅ ¡COINCIDENCIA POR NÚMERO LOCAL (mobile)! Empleado: {employee.name}")
                        return employee

                    if len(work_normalized) >= 9 and local_incoming == work_normalized[-9:]:
                        print(f"✅ ¡COINCIDENCIA POR NÚMERO LOCAL (work)! Empleado: {employee.name}")
                        return employee

            print(f"❌ No se encontró empleado con el número normalizado: {normalized_incoming}")

            # Búsqueda fallback usando LIKE (método anterior como respaldo)
            print("🔄 Intentando búsqueda fallback con LIKE...")
            clean_phone = re.sub(r'[^\d]', '', phone_number)

            domain = [
                '|', '|', '|',
                ('mobile_phone', 'ilike', phone_number),
                ('work_phone', 'ilike', phone_number),
                ('mobile_phone', 'ilike', clean_phone),
                ('work_phone', 'ilike', clean_phone)
            ]

            if len(clean_phone) > 9:
                local_phone = clean_phone[-9:]
                domain.extend([
                    '|', '|',
                    ('mobile_phone', 'ilike', local_phone),
                    ('work_phone', 'ilike', local_phone)
                ])

            employee = request.env['hr.employee'].sudo().search(domain, limit=1)

            if employee:
                print(f"✅ Empleado encontrado con búsqueda fallback: {employee.name}")
            else:
                print(f"❌ No se encontró empleado ni con búsqueda fallback")

            return employee

        except Exception as e:
            print(f"❌ Error buscando empleado: {e}")
            _logger.error("Error buscando empleado por teléfono: %s", e)
            return None

    def _register_attendance(self, employee, attendance_type):
        """
        Registra la asistencia del empleado usando los métodos nativos de Odoo
        """
        try:
            print(f"📝 Registrando asistencia: {attendance_type} para {employee.name}")
            print(f"📊 Estado actual del empleado: {employee.attendance_state}")

            if attendance_type == 'check_in':
                # Verificar si ya está trabajando
                if employee.attendance_state == 'checked_in':
                    print(f"⚠️ El empleado ya está marcado como presente")
                    return False

                print(f"🔄 Usando método nativo de Odoo para entrada...")
                # Usar el método nativo para check-in
                attendance = employee.sudo()._attendance_action_change()

                print(f"✅ Entrada registrada con método nativo - ID: {attendance.id}")
                return attendance

            elif attendance_type == 'check_out':
                # Verificar si está trabajando
                if employee.attendance_state == 'checked_out':
                    print(f"⚠️ El empleado ya está marcado como ausente")
                    return False

                print(f"🔄 Usando método nativo de Odoo para salida...")
                # Usar el método nativo para check-out
                attendance = employee.sudo()._attendance_action_change()

                print(f"✅ Salida registrada con método nativo - ID: {attendance.id}")
                return attendance

            return False

        except Exception as e:
            print(f"❌ Error registrando asistencia: {e}")
            _logger.error("Error registrando asistencia: %s", e)

            return False

    def _handle_overtime_duplicate_error(self, employee, attendance_type):
        """
        Maneja específicamente los errores de duplicados en horas extras
        """
        try:
            today = datetime.now().date()

            # Limpiar registros duplicados de horas extras
            print("🧹 Limpiando registros duplicados de horas extras...")
            overtime_records = request.env['hr.attendance.overtime'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '=', today)
            ])

            if len(overtime_records) > 1:
                print(f"   Encontrados {len(overtime_records)} registros duplicados")
                # Eliminar todos los registros de horas extras de hoy para este empleado
                overtime_records.sudo().unlink()
                print("   ✅ Registros duplicados eliminados")

                # Hacer commit para aplicar los cambios
                request.env.cr.commit()

            # Intentar registrar la asistencia nuevamente
            print("🔄 Reintentando registro de asistencia...")

            if attendance_type == 'check_in':
                # Verificar nuevamente si existe entrada
                existing_attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                    ('check_out', '=', False)
                ], limit=1)

                if existing_attendance:
                    print(f"⚠️ El empleado ya tiene una entrada registrada")
                    return False

                # Crear entrada
                attendance = request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': datetime.now(),
                })

                print(f"✅ Entrada registrada después de limpiar duplicados - ID: {attendance.id}")
                return attendance

            elif attendance_type == 'check_out':
                # Buscar entrada abierta
                existing_attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if not existing_attendance:
                    print(f"⚠️ No se encontró entrada previa para registrar salida")
                    return False

                # Registrar salida
                existing_attendance.sudo().write({
                    'check_out': datetime.now()
                })

                print(f"✅ Salida registrada después de limpiar duplicados - ID: {existing_attendance.id}")
                return existing_attendance

        except Exception as e2:
            print(f"❌ Error al manejar duplicados de horas extras: {e2}")
            _logger.error("Error manejando duplicados de horas extras: %s", e2)
            return False

    def _send_confirmation_message(self, phone_number, attendance_type, employee):
        """
        Envía mensaje de confirmación al empleado via WhatsApp
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Obtener la hora real de la asistencia registrada
            today = datetime.now().date()
            if attendance_type == 'check_in':
                # Buscar la entrada más reciente de hoy
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if attendance and attendance.check_in:
                    # Convertir a hora local y formatear
                    attendance_time = attendance.check_in.strftime("%H:%M")
                    print(f"🕐 Hora real de entrada: {attendance_time}")
                else:
                    attendance_time = datetime.now().strftime("%H:%M")
                    print(f"⚠️ No se encontró registro de entrada, usando hora actual: {attendance_time}")

            else:  # check_out
                # Buscar la asistencia con salida más reciente de hoy
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                    ('check_out', '!=', False)
                ], limit=1, order='check_out desc')

                if attendance and attendance.check_out:
                    # Convertir a hora local y formatear
                    attendance_time = attendance.check_out.strftime("%H:%M")
                    print(f"🕐 Hora real de salida: {attendance_time}")
                else:
                    attendance_time = datetime.now().strftime("%H:%M")
                    print(f"⚠️ No se encontró registro de salida, usando hora actual: {attendance_time}")

            date_now = datetime.now().strftime("%d/%m/%Y")

            message = f"✅ Hola {employee.name},\n\nTu *{action_text}* ha sido registrada correctamente.\n\n🕐 Hora: {attendance_time}\n📅 Fecha: {date_now}\n\n¡Que tengas un buen día!"

            print(f"📤 Enviando confirmación a {phone_number}: {message}")

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            print(f"📱 Usando cuenta WhatsApp: {wa_account.name}")

            # Enviar mensaje usando la API de WhatsApp
            success = self._send_whatsapp_message(wa_account, phone_number, message)

            if success:
                print(f"✅ Mensaje de confirmación enviado exitosamente")
                return True
            else:
                print(f"❌ Error enviando mensaje de confirmación")
                return False

        except Exception as e:
            print(f"❌ Error enviando confirmación: {e}")
            _logger.error("Error enviando confirmación de asistencia: %s", e)
            return False

    def _send_error_message(self, phone_number, error_message):
        """
        Envía mensaje de error al remitente
        """
        try:
            message = f"❌ *Error de Asistencia*\n\n{error_message}\n\nPor favor, contacta con Recursos Humanos si el problema persiste."

            print(f"📤 Enviando error a {phone_number}: {message}")

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            # Enviar mensaje
            success = self._send_whatsapp_message(wa_account, phone_number, message)

            if success:
                print(f"✅ Mensaje de error enviado exitosamente")
                return True
            else:
                print(f"❌ Error enviando mensaje de error")
                return False

        except Exception as e:
            print(f"❌ Error enviando mensaje de error: {e}")
            _logger.error("Error enviando mensaje de error: %s", e)
            return False

    def _send_whatsapp_message(self, wa_account, phone_number, message):
        """
        Envía un mensaje de WhatsApp usando la API
        """
        try:
            import requests

            # Obtener el token de acceso (puede estar en diferentes campos según la versión)
            access_token = None

            # Intentar diferentes nombres de campos para el token
            token_fields = ['access_token', 'token', 'app_secret', 'permanent_access_token']

            for field in token_fields:
                if hasattr(wa_account, field):
                    token_value = getattr(wa_account, field)
                    if token_value:
                        access_token = token_value
                        print(f"🔑 Token encontrado en campo: {field}")
                        break

            if not access_token:
                print(f"❌ No se encontró token de acceso en la cuenta de WhatsApp")
                print(f"   Campos disponibles: {[field for field in dir(wa_account) if not field.startswith('_') and 'token' in field.lower()]}")
                return False

            # URL de la API de WhatsApp Business
            url = f"https://graph.facebook.com/v18.0/{wa_account.phone_uid}/messages"

            # Headers de la petición
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Limpiar el número de teléfono (quitar el + si existe)
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

            print(f"📡 Enviando a API WhatsApp:")
            print(f"   URL: {url}")
            print(f"   Teléfono: {clean_phone}")
            print(f"   Token: {access_token[:20]}..." if access_token else "Sin token")
            print(f"   Mensaje: {message[:50]}...")

            # Realizar la petición
            response = requests.post(url, headers=headers, json=data, timeout=10)

            print(f"📨 Respuesta API: {response.status_code}")
            print(f"📄 Contenido: {response.text}")

            if response.status_code == 200:
                return True
            else:
                print(f"❌ Error en API WhatsApp: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error llamando API WhatsApp: {e}")
            _logger.error("Error llamando API WhatsApp: %s", e)
            return False

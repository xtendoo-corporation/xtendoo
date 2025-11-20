import logging
import json
import re
from datetime import datetime
import tempfile
import requests
import pytz
from odoo.tools.misc import file_path
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
                            elif message.get('type') == 'location':
                                # Manejar mensajes de ubicación directamente
                                self._handle_attendance_message(message, value)
                            elif message.get('type') == 'interactive':
                                # Manejar respuestas de botones interactivos
                                print(f"🔘 Procesando mensaje interactivo (botón presionado)")
                                self._handle_attendance_message(message, value)

                            # Detectar comando de asistencia '/asistencia'
                            text_content = message.get('text', {}).get('body', '').strip().lower()
                            if text_content == '/asistencia':
                                phone_number = message.get('from', '')
                                employee = self._find_employee_by_phone(phone_number)
                                if employee:
                                    self._send_attendance_report(phone_number, employee)
                                else:
                                    self._send_error_message(phone_number, "No se encontró empleado asociado a este número")
                                continue  # No procesar como comando normal

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
            message_id = message.get('id', '')
            timestamp = message.get('timestamp', '')

            print(f"\n📋 Procesando mensaje de asistencia:")
            print(f"   Teléfono: {phone_number}")
            print(f"   ID Mensaje: {message_id}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Tipo: {message.get('type')}")

            # Procesar mensajes de texto normales
            text_content = message.get('text', {}).get('body', '').strip().lower() if message.get('type') == 'text' else ''
            print(f"   Texto: '{text_content}'")

            # Detectar comando de asistencia
            attendance_type = self._detect_attendance_command(text_content)

            if attendance_type == 'attendance_report':
                # Flujo especial para /asistencia
                employee = self._find_employee_by_phone(phone_number)
                if employee:
                    self._send_attendance_report(phone_number, employee)
                else:
                    self._send_error_message(phone_number, "No se encontró empleado asociado a este número")
                return

            if attendance_type:
                print(f"✅ Comando detectado: {attendance_type}")

                # Buscar empleado por número de teléfono
                employee = self._find_employee_by_phone(phone_number)

                if employee:
                    print(f"👤 Empleado encontrado: {employee.name} (ID: {employee.id})")
                    # Validar estado de asistencia antes de proceder
                    validation_result = self._validate_attendance_state(employee, attendance_type)
                    if not validation_result['valid']:
                        print(f"❌ Validación fallida: {validation_result['message']}")
                        self._send_error_message(phone_number, validation_result['message'])
                        return

                    # Verificar si tiene geolocalización activada
                    if employee.whatsapp_geotrack_enabled:
                        print(f"🗺️ Geolocalización activada para {employee.name}")
                        # Solicitar ubicación antes de registrar asistencia
                        self._request_location_for_attendance(phone_number, employee, attendance_type)
                        return
                    else:
                        print(f"ℹ️ Geolocalización desactivada para {employee.name}")

                    # Registrar asistencia sin geolocalización
                    attendance_result = self._register_attendance(employee, attendance_type, validation_result)

                    if attendance_result:
                        print(f"✅ Asistencia registrada exitosamente")
                        self._send_confirmation_message(phone_number, attendance_type, employee)
                    else:
                        print(f"❌ Error al registrar asistencia")
                        self._send_error_message(phone_number, "Error al registrar asistencia")
                else:
                    print(f"❌ No se encontró empleado con el teléfono: {phone_number}")
                    self._send_error_message(phone_number, "No se encontró empleado asociado a este número")
            else:
                # Verificar si es una respuesta de ubicación
                location_data = self._extract_location_from_message(message, value)
                if location_data:
                    self._process_location_response(phone_number, location_data)
                else:
                    print(f"ℹ️ Mensaje no es comando de asistencia: '{text_content}'")

        except Exception as e:
            print(f"❌ Error manejando mensaje de asistencia: {e}")
            _logger.error("Error manejando mensaje de asistencia: %s", e)

    def _detect_attendance_command(self, text):
        """
        Detecta si el texto contiene un comando de asistencia válido
        Retorna 'check_in', 'check_out' o None
        Usa configuración de base de datos en lugar de patrones hardcodeados
        """
        # Normalizar texto (quitar acentos, espacios extra, etc.)
        normalized_text = re.sub(r'\s+', ' ', text.lower().strip())

        # Obtener palabras clave de entrada desde configuración
        entrada_keywords = request.env['attendance.keyword.config'].sudo().get_active_keywords('check_in')

        # Obtener palabras clave de salida desde configuración
        salida_keywords = request.env['attendance.keyword.config'].sudo().get_active_keywords('check_out')

        print(f"🔍 Palabras clave configuradas:")
        print(f"   Entrada: {entrada_keywords}")
        print(f"   Salida: {salida_keywords}")

        # Permitir comando especial /asistencia
        if normalized_text == '/asistencia':
            print("✅ Comando especial /asistencia detectado")
            return 'attendance_report'

        # Buscar patrones de entrada
        for keyword in entrada_keywords:
            keyword_lower = keyword.lower()

            # Para palabras clave que empiezan con caracteres especiales (como /entrada)
            # usamos coincidencia exacta o al inicio/final de línea
            if keyword_lower.startswith('/') or keyword_lower.startswith('#') or keyword_lower.startswith('!'):
                # Buscar coincidencia exacta o al inicio de línea/palabra
                patterns = [
                    r'^' + re.escape(keyword_lower) + r'$',  # Coincidencia exacta
                    r'^' + re.escape(keyword_lower) + r'\s',  # Al inicio seguido de espacio
                    r'\s' + re.escape(keyword_lower) + r'$',  # Al final precedido de espacio
                    r'\s' + re.escape(keyword_lower) + r'\s'  # En medio con espacios
                ]
            else:
                # Para palabras normales, usar límites de palabra tradicionales
                patterns = [r'\b' + re.escape(keyword_lower) + r'\b']

            # Probar todos los patrones
            for pattern in patterns:
                if re.search(pattern, normalized_text):
                    print(f"✅ Coincidencia encontrada para ENTRADA: '{keyword}' con patrón: {pattern}")
                    return 'check_in'

            # También probar coincidencia simple sin regex para casos especiales
            if keyword_lower == normalized_text or keyword_lower in normalized_text:
                print(f"✅ Coincidencia simple encontrada para ENTRADA: '{keyword}'")
                return 'check_in'

        # Buscar patrones de salida con la misma lógica
        for keyword in salida_keywords:
            keyword_lower = keyword.lower()

            # Para palabras clave que empiezan con caracteres especiales
            if keyword_lower.startswith('/') or keyword_lower.startswith('#') or keyword_lower.startswith('!'):
                patterns = [
                    r'^' + re.escape(keyword_lower) + r'$',  # Coincidencia exacta
                    r'^' + re.escape(keyword_lower) + r'\s',  # Al inicio seguido de espacio
                    r'\s' + re.escape(keyword_lower) + r'$',  # Al final precedido de espacio
                    r'\s' + re.escape(keyword_lower) + r'\s'  # En medio con espacios
                ]
            else:
                patterns = [r'\b' + re.escape(keyword_lower) + r'\b']

            # Probar todos los patrones
            for pattern in patterns:
                if re.search(pattern, normalized_text):
                    print(f"✅ Coincidencia encontrada para SALIDA: '{keyword}' con patrón: {pattern}")
                    return 'check_out'

            # También probar coincidencia simple
            if keyword_lower == normalized_text or keyword_lower in normalized_text:
                print(f"✅ Coincidencia simple encontrada para SALIDA: '{keyword}'")
                return 'check_out'

        print(f"❌ No se encontraron coincidencias para: '{normalized_text}'")
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

    def _register_attendance(self, employee, attendance_type, validation_result=None):
        """
        Registra la asistencia del empleado usando los métodos nativos de Odoo
        Para check_out: usa la entrada pendiente encontrada en la validación
        """
        try:
            print(f"📝 Registrando asistencia: {attendance_type} para {employee.name}")
            print(f"📊 Estado actual del empleado: {employee.attendance_state}")

            if attendance_type == 'check_in':
                # Para entrada, verificar que no esté ya trabajando
                if employee.attendance_state == 'checked_in':
                    print(f"⚠️ El empleado ya está marcado como presente")
                    return False

                print(f"🔄 Usando método nativo de Odoo para entrada...")
                # Usar el método nativo para check-in
                attendance = employee.sudo()._attendance_action_change()

                print(f"✅ Entrada registrada con método nativo - ID: {attendance.id}")
                return attendance

            elif attendance_type == 'check_out':
                # Para salida, usar la entrada pendiente encontrada en la validación
                if validation_result and 'open_attendance' in validation_result:
                    open_attendance = validation_result['open_attendance']
                    print(f"📋 Usando entrada pendiente encontrada en validación: ID {open_attendance.id}")

                    # Registrar la salida directamente en el registro de entrada pendiente
                    open_attendance.sudo().write({
                        'check_out': datetime.now()
                    })

                    check_in_date = open_attendance.check_in.strftime('%d/%m/%Y %H:%M')
                    check_out_date = datetime.now().strftime('%d/%m/%Y %H:%M')
                    print(f"✅ Salida registrada - Entrada: {check_in_date}, Salida: {check_out_date}")
                    return open_attendance
                else:
                    # Fallback: buscar entrada pendiente manualmente
                    print(f"🔍 Buscando entrada pendiente manualmente...")
                    open_attendance = request.env['hr.attendance'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('check_out', '=', False)
                    ], limit=1, order='check_in desc')

                    if not open_attendance:
                        print(f"❌ No se encontró entrada pendiente")
                        return False

                    # Registrar la salida
                    open_attendance.sudo().write({
                        'check_out': datetime.now()
                    })

                    print(f"✅ Salida registrada en entrada ID: {open_attendance.id}")
                    return open_attendance

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
        Usa plantillas de WhatsApp aprobadas desde base de datos
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Obtener la zona horaria del usuario o del sistema
            user_tz = request.env.user.tz or 'Europe/Madrid'  # Por defecto España
            local_tz = pytz.timezone(user_tz)

            print(f"🌍 Zona horaria detectada: {user_tz}")

            # Obtener la hora real de la asistencia registrada
            today = datetime.now().date()
            attendance = None
            if attendance_type == 'check_in':
                # Buscar la entrada más reciente de hoy
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                ], limit=1, order='check_in desc')
            else:  # check_out
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '!=', False)
                ], limit=1, order='check_out desc')

            if attendance:
                if attendance_type == 'check_in' and attendance.check_in:
                    utc_time = attendance.check_in.replace(tzinfo=pytz.UTC)
                    local_time = utc_time.astimezone(local_tz)
                    attendance_time = local_time.strftime("%H:%M")
                elif attendance_type == 'check_out' and attendance.check_out:
                    utc_time = attendance.check_out.replace(tzinfo=pytz.UTC)
                    local_time = utc_time.astimezone(local_tz)
                    attendance_time = local_time.strftime("%H:%M")
                else:
                    now_local = datetime.now(local_tz)
                    attendance_time = now_local.strftime("%H:%M")
            else:
                now_local = datetime.now(local_tz)
                attendance_time = now_local.strftime("%H:%M")

            date_now = datetime.now().strftime("%d/%m/%Y")

            # Mensaje por defecto
            message = f"✅ Hola {employee.name},\n\nTu *{action_text}* ha sido registrada correctamente.\n\n🕐 Hora: {attendance_time}\n📅 Fecha: {date_now}\n\n¡Que tengas un buen día!"

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            print(f"📱 Usando cuenta WhatsApp: {wa_account.name}")

            # Enviar mensaje de texto libre
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

    def _send_confirmation_message_with_location(self, phone_number, attendance_type, employee, location_data):
        """
        Envía mensaje de confirmación al empleado via WhatsApp incluyendo la ubicación
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"
            user_tz = request.env.user.tz or 'Europe/Madrid'
            local_tz = pytz.timezone(user_tz)
            today = datetime.now().date()
            attendance = None
            if attendance_type == 'check_in':
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', f"{today} 00:00:00"),
                ], limit=1, order='check_in desc')
            else:
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '!=', False)
                ], limit=1, order='check_out desc')

            if attendance:
                if attendance_type == 'check_in' and attendance.check_in:
                    utc_time = attendance.check_in.replace(tzinfo=pytz.UTC)
                    local_time = utc_time.astimezone(local_tz)
                    attendance_time = local_time.strftime("%H:%M")
                elif attendance_type == 'check_out' and attendance.check_out:
                    utc_time = attendance.check_out.replace(tzinfo=pytz.UTC)
                    local_time = utc_time.astimezone(local_tz)
                    attendance_time = local_time.strftime("%H:%M")
                else:
                    now_local = datetime.now(local_tz)
                    attendance_time = now_local.strftime("%H:%M")
            else:
                now_local = datetime.now(local_tz)
                attendance_time = now_local.strftime("%H:%M")

            date_now = datetime.now().strftime("%d/%m/%Y")

            lat = location_data.get('latitude')
            lng = location_data.get('longitude')
            address = location_data.get('address', '')
            maps_url = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else ''
            message = f"✅ Hola {employee.name},\n\nTu *{action_text}* ha sido registrada correctamente con ubicación.\n\n🕐 Hora: {attendance_time}\n📅 Fecha: {date_now}\n"
            if lat and lng:
                message += f"\n📍 Coordenadas: {lat}, {lng}\n🗺️ Ver en Google Maps: {maps_url}"
            if address:
                message += f"\nDirección: {address}"
            message += "\n\n¡Que tengas un buen día!"

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            print(f"📱 Usando cuenta WhatsApp: {wa_account.name}")

            # Enviar mensaje de texto libre
            success = self._send_whatsapp_message(wa_account, phone_number, message)

            if success:
                print(f"✅ Mensaje de confirmación con ubicación enviado exitosamente")
                return True
            else:
                print(f"❌ Error enviando mensaje de confirmación con ubicación")
                return False

        except Exception as e:
            print(f"❌ Error enviando confirmación con ubicación: {e}")
            _logger.error("Error enviando confirmación de asistencia con ubicación: %s", e)
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

    def _send_whatsapp_message(self, wa_account, phone_number, message, template_id=None, template_params=None):
        """
        Envía un mensaje de WhatsApp usando la API
        Soporta tanto mensajes de texto libre como plantillas aprobadas
        """
        try:
            # Obtener el token de acceso
            access_token = None
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
                return False
            url = f"https://graph.facebook.com/v18.0/{wa_account.phone_uid}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            clean_phone = phone_number.lstrip('+')
            # Datos del mensaje
            if template_id and template_params:
                # Usar plantilla de WhatsApp
                data = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "template",
                    "template": {
                        "name": template_id,
                        "language": {
                            "code": "es"
                        },
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": param
                                    } for param in template_params
                                ]
                            }
                        ]
                    }
                }
                print(f"📋 Enviando plantilla: {template_id}")
                print(f"📋 Parámetros: {template_params}")
            else:
                # Usar mensaje de texto libre
                data = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }
                print(f"📝 Enviando texto libre")
            print(f"📡 Enviando a API WhatsApp:")
            print(f"   URL: {url}")
            print(f"   Teléfono: {clean_phone}")
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

    def _request_location_for_attendance(self, phone_number, employee, attendance_type):
        """
        Solicita la ubicación al empleado directamente con instrucciones
        MODIFICADO: En este módulo NO se pregunta, se solicita directamente la ubicación
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"

            # Guardar temporalmente la solicitud pendiente
            request.env['ir.config_parameter'].sudo().set_param(
                f'whatsapp_attendance_pending_{phone_number}',
                f'{employee.id}|{attendance_type}'
            )

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            print(f"📍 Solicitando ubicación DIRECTAMENTE a {employee.name} para {attendance_type}")

            # Enviar mensaje directo con instrucciones para compartir ubicación
            success = self._send_direct_location_request(wa_account, phone_number, employee, action_text)

            if success:
                print(f"✅ Solicitud directa de ubicación enviada exitosamente")
                return True
            else:
                print(f"❌ Error enviando solicitud de ubicación, registrando sin ubicación...")
                # Si falla, registrar sin ubicación
                self._register_attendance_without_location(employee, attendance_type, phone_number)
                return False

        except Exception as e:
            print(f"❌ Error solicitando ubicación: {e}")
            _logger.error("Error solicitando ubicación: %s", e)
            # Si hay error, registrar sin ubicación
            self._register_attendance_without_location(employee, attendance_type, phone_number)
            return False

    def _send_location_request_with_button(self, wa_account, phone_number, employee, action_text):
        """
        Envía una plantilla de WhatsApp con botones integrados para solicitar ubicación
        """
        try:
            import requests

            # Obtener token de acceso
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

            # Buscar plantilla de solicitud de ubicación con botones
            location_template = self._get_location_request_template()

            if location_template:
                # Usar plantilla de WhatsApp con botones integrados
                print(f"📋 Usando plantilla con botones: {location_template}")

                template_params = [employee.name, action_text]

                data = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "template",
                    "template": {
                        "name": location_template,
                        "language": {
                            "code": "es"
                        },
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": param
                                    } for param in template_params
                                ]
                            }
                        ]
                    }
                }

                print(f"📋 Enviando plantilla con botones integrados:")
                print(f"   Plantilla: {location_template}")
                print(f"   Parámetros: {template_params}")

                response = requests.post(url, headers=headers, json=data, timeout=10)

                if response.status_code == 200:
                    print(f"✅ Plantilla con botones enviada exitosamente")
                    return True
                else:
                    print(f"⚠️ Plantilla falló: {response.text}")
                    print(f"🔄 Cambiando a mensaje interactivo fallback...")

            # Fallback: Mensaje interactivo si la plantilla no funciona
            data = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": f"📍 Hola {employee.name}!\n\nPara registrar tu {action_text}, ¿deseas compartir tu ubicación?"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "share_location",
                                    "title": "📍 Con ubicación"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "no_location",
                                    "title": "✅ Sin ubicación"
                                }
                            }
                        ]
                    }
                }
            }

            print(f"📋 Enviando mensaje interactivo fallback")
            response = requests.post(url, headers=headers, json=data, timeout=10)

            print(f"📡 Solicitud enviada:")
            print(f"   Teléfono: {clean_phone}")
            print(f"   Empleado: {employee.name}")
            print(f"📨 Respuesta API: {response.status_code}")
            print(f"📄 Contenido: {response.text}")

            return response.status_code == 200

        except Exception as e:
            print(f"❌ Error enviando solicitud de ubicación: {e}")
            return False

    def _send_direct_location_request(self, wa_account, phone_number, employee, action_text):
        """
        Envía mensaje directo solicitando ubicación SIN botones
        NUEVO: Este método envía instrucciones directas para compartir ubicación
        """
        try:
            print(f"📍 Enviando solicitud DIRECTA de ubicación a {employee.name}")

            # Mensaje directo con instrucciones claras
            message = f"""📍 *Hola {employee.name}!*

Para registrar tu *{action_text}*, necesito que compartas tu ubicación.

*Instrucciones:*
1️⃣ Toca el botón 📎 (clip) en WhatsApp
2️⃣ Selecciona *Ubicación*
3️⃣ Elige *Ubicación actual*
4️⃣ Envía tu ubicación

⏰ Tienes 3 minutos para enviarla.

_Tu asistencia se registrará una vez que reciba tu ubicación._"""

            # Enviar mensaje de texto simple
            success = self._send_whatsapp_message(wa_account, phone_number, message)

            if success:
                print(f"✅ Solicitud directa de ubicación enviada exitosamente")
                return True
            else:
                print(f"❌ Error enviando solicitud directa de ubicación")
                return False

        except Exception as e:
            print(f"❌ Error enviando solicitud directa de ubicación: {e}")
            _logger.error("Error enviando solicitud directa de ubicación: %s", e)
            return False

    def _extract_location_from_message(self, message, value):
        """
        Extrae datos de ubicación de un mensaje de WhatsApp
        """
        try:
            # Verificar si el mensaje contiene ubicación
            if message.get('type') == 'location':
                location_data = message.get('location', {})
                print(f"📍 Ubicación recibida: {location_data}")
                return {
                    'latitude': location_data.get('latitude'),
                    'longitude': location_data.get('longitude'),
                    'name': location_data.get('name', ''),
                    'address': location_data.get('address', '')
                }

            # También verificar en mensajes de texto que contengan coordenadas
            if message.get('type') == 'text':
                text = message.get('text', {}).get('body', '')
                # Buscar patrones de coordenadas en texto
                coord_pattern = r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)'
                match = re.search(coord_pattern, text)
                if match:
                    print(f"📍 Coordenadas encontradas en texto: {match.groups()}")
                    return {
                        'latitude': float(match.group(1)),
                        'longitude': float(match.group(2)),
                        'name': '',
                        'address': text
                    }

            return None

        except Exception as e:
            print(f"❌ Error extrayendo ubicación: {e}")
            return None

    def _process_location_response(self, phone_number, location_data):
        """
        Procesa la respuesta de ubicación y registra la asistencia o añade ubicación a registro existente
        MODIFICADO: Ahora maneja dos casos:
        1. Registro normal con ubicación (flujo anterior)
        2. Añadir ubicación a asistencia ya registrada (nuevo flujo)
        """
        try:
            # Obtener solicitud pendiente
            pending_key = f'whatsapp_attendance_pending_{phone_number}'
            pending_data = request.env['ir.config_parameter'].sudo().get_param(pending_key)

            if not pending_data:
                print(f"⚠️ No hay solicitud de asistencia pendiente para {phone_number}")
                self._send_error_message(phone_number, "No hay registro de asistencia pendiente")
                return False

            # Parsear datos pendientes
            pending_parts = pending_data.split('|')
            employee_id = int(pending_parts[0])
            attendance_type = pending_parts[1]

            # Verificar si hay ID de asistencia (nuevo flujo)
            attendance_id = int(pending_parts[2]) if len(pending_parts) > 2 else None

            employee = request.env['hr.employee'].sudo().browse(employee_id)

            if not employee.exists():
                print(f"❌ Empleado no encontrado: {employee_id}")
                return False

            print(f"📍 Procesando ubicación para {employee.name}: {location_data}")

            if attendance_id:
                # NUEVO FLUJO: Añadir ubicación a asistencia ya registrada
                print(f"🔄 NUEVO FLUJO: Añadiendo ubicación a asistencia existente ID: {attendance_id}")

                attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
                if not attendance.exists():
                    print(f"❌ Registro de asistencia no encontrado: {attendance_id}")
                    self._send_error_message(phone_number, "Registro de asistencia no encontrado")
                    return False

                # Añadir ubicación al registro existente
                success = self._add_location_to_existing_attendance(attendance, location_data)

                if success:
                    # Limpiar solicitud pendiente
                    request.env['ir.config_parameter'].sudo().set_param(pending_key, False)

                    # Enviar confirmación de ubicación añadida
                    self._send_location_added_confirmation(phone_number, attendance_type, employee, location_data)

                    print(f"✅ Ubicación añadida exitosamente al registro {attendance_id}")
                    return True
                else:
                    print(f"❌ Error añadiendo ubicación al registro")
                    self._send_error_message(phone_number, "Error al añadir ubicación")
                    return False

            else:
                # FLUJO ANTERIOR: Registrar asistencia con ubicación
                print(f"🔄 FLUJO ANTERIOR: Registrando asistencia con ubicación")

                attendance_result = self._register_attendance_with_location(
                    employee, attendance_type, location_data
                )

                if attendance_result:
                    # Limpiar solicitud pendiente
                    request.env['ir.config_parameter'].sudo().set_param(pending_key, False)

                    # Enviar confirmación
                    self._send_confirmation_message_with_location(
                        phone_number, attendance_type, employee, location_data
                    )

                    print(f"✅ Asistencia con ubicación registrada exitosamente")
                    return True
                else:
                    print(f"❌ Error registrando asistencia con ubicación")
                    self._send_error_message(phone_number, "Error al registrar asistencia")
                    return False

        except Exception as e:
            print(f"❌ Error procesando ubicación: {e}")
            _logger.error("Error procesando ubicación: %s", e)
            return False

    def _register_attendance_with_location(self, employee, attendance_type, location_data):
        """
        Registra asistencia incluyendo datos de geolocalización
        """
        try:
            print(f"📝 Registrando asistencia CON ubicación: {attendance_type} para {employee.name}")

            # Registrar asistencia normal
            attendance = self._register_attendance(employee, attendance_type)

            if not attendance:
                return False

            # Obtener dirección aproximada
            address = self._get_address_from_coordinates(
                location_data.get('latitude'),
                location_data.get('longitude')
            )

            # Actualizar registro de asistencia con ubicación según tipo
            vals = {}
            if attendance_type == 'check_in':
                vals = {
                    'whatsapp_check_in_latitude': location_data.get('latitude'),
                    'whatsapp_check_in_longitude': location_data.get('longitude'),
                    'whatsapp_check_in_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_in_location_accuracy': location_data.get('accuracy', 0.0)
                }
            elif attendance_type == 'check_out':
                vals = {
                    'whatsapp_check_out_latitude': location_data.get('latitude'),
                    'whatsapp_check_out_longitude': location_data.get('longitude'),
                    'whatsapp_check_out_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_out_location_accuracy': location_data.get('accuracy', 0.0)
                }
            attendance.sudo().write(vals)

            # Actualizar última ubicación del empleado
            employee.sudo().write({
                'last_whatsapp_latitude': location_data.get('latitude'),
                'last_whatsapp_longitude': location_data.get('longitude'),
                'last_whatsapp_location_time': datetime.now(),
                'last_whatsapp_address': address or location_data.get('address', '')
            })

            print(f"✅ Ubicación guardada: {location_data.get('latitude')}, {location_data.get('longitude')}")
            return attendance

        except Exception as e:
            print(f"❌ Error registrando asistencia con ubicación: {e}")
            _logger.error("Error registrando asistencia con ubicación: %s", e)
            return False

    def _add_location_to_existing_attendance(self, attendance, location_data):
        """
        Añade datos de ubicación a un registro de asistencia ya existente
        """
        try:
            print(f"📍 Añadiendo ubicación al registro de asistencia ID: {attendance.id}")

            # Obtener dirección aproximada
            address = self._get_address_from_coordinates(
                location_data.get('latitude'),
                location_data.get('longitude')
            )

            # Determinar si es entrada o salida según si check_out está vacío
            vals = {}
            if not attendance.check_out:
                # Si no hay salida, es entrada
                vals = {
                    'whatsapp_check_in_latitude': location_data.get('latitude'),
                    'whatsapp_check_in_longitude': location_data.get('longitude'),
                    'whatsapp_check_in_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_in_location_accuracy': location_data.get('accuracy', 0.0)
                }
            else:
                # Si hay salida, es salida
                vals = {
                    'whatsapp_check_out_latitude': location_data.get('latitude'),
                    'whatsapp_check_out_longitude': location_data.get('longitude'),
                    'whatsapp_check_out_location_address': address or location_data.get('address', ''),
                    'whatsapp_check_out_location_accuracy': location_data.get('accuracy', 0.0)
                }
            attendance.sudo().write(vals)

            # Actualizar última ubicación del empleado
            employee = attendance.employee_id
            employee.sudo().write({
                'last_whatsapp_latitude': location_data.get('latitude'),
                'last_whatsapp_longitude': location_data.get('longitude'),
                'last_whatsapp_location_time': datetime.now(),
                'last_whatsapp_address': address or location_data.get('address', '')
            })

            print(f"✅ Ubicación añadida exitosamente: {location_data.get('latitude')}, {location_data.get('longitude')}")
            return True

        except Exception as e:
            print(f"❌ Error añadiendo ubicación al registro: {e}")
            _logger.error("Error añadiendo ubicación al registro: %s", e)
            return False

    def _send_location_added_confirmation(self, phone_number, attendance_type, employee, location_data):
        """
        Envía confirmación de que la ubicación ha sido añadida al registro de asistencia
        """
        try:
            action_text = "entrada" if attendance_type == 'check_in' else "salida"
            lat = location_data.get('latitude')
            lng = location_data.get('longitude')

            if lat and lng:
                location_message = f"🎉 *¡Ubicación añadida exitosamente!*\n\nTu {action_text} ahora incluye tu ubicación:\n\n📍 Coordenadas: {lat:.6f}, {lng:.6f}\n\n🗺️ Ver en Google Maps: https://maps.google.com/?q={lat},{lng}\n\n✅ Registro completado"

                # Buscar cuenta WhatsApp
                wa_account = request.env['whatsapp.account'].sudo().search([
                    ('active', '=', True)
                ], limit=1)

                if wa_account:
                    success = self._send_whatsapp_message(wa_account, phone_number, location_message)

                    if success:
                        print(f"✅ Confirmación de ubicación añadida enviada exitosamente")
                        return True
                    else:
                        print(f"❌ Error enviando confirmación de ubicación añadida")
                        return False

            return False

        except Exception as e:
            print(f"❌ Error enviando confirmación de ubicación añadida: {e}")
            _logger.error("Error enviando confirmación de ubicación añadida: %s", e)
            return False

    def _get_location_request_template(self):
        """
        Obtiene el nombre de la plantilla de WhatsApp para solicitar ubicación
        desde la configuración de base de datos
        """
        try:
            # Buscar configuración de plantilla de ubicación
            config = request.env['ir.config_parameter'].sudo()
            template_name = config.get_param('whatsapp_attendance.location_request_template')

            if template_name:
                print(f"📋 Plantilla de ubicación configurada: {template_name}")
                return template_name
            else:
                print(f"⚠️ No hay plantilla de ubicación configurada")
                return None

        except Exception as e:
            print(f"❌ Error obteniendo plantilla de ubicación: {e}")
            return None

    def _get_address_from_coordinates(self, latitude, longitude):
        """
        Obtiene dirección aproximada desde coordenadas usando servicio de geocoding
        """
        try:
            # Por ahora, retorna un placeholder
            if latitude and longitude:
                return f"Ubicación aproximada: {latitude:.6f}, {longitude:.6f}"

            return None

        except Exception as e:
            print(f"⚠️ Error obteniendo dirección: {e}")
            return None

    def _send_location_sharing_instructions(self, phone_number):
        """
        Envía instrucciones para compartir ubicación cuando el usuario elige el botón correspondiente
        """
        try:
            print(f"📍 Enviando instrucciones para compartir ubicación a {phone_number}")

            # Buscar plantilla de instrucciones de ubicación
            instruction_template = self._get_location_instruction_template()

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False

            if instruction_template:
                # Usar plantilla de WhatsApp para instrucciones
                print(f"📋 Usando plantilla de instrucciones: {instruction_template}")

                success = self._send_whatsapp_message(
                    wa_account,
                    phone_number,
                    message=None,
                    template_id=instruction_template,
                    template_params=[]
                )
            else:
                # Usar mensaje de texto libre como fallback
                message = f"📍 *Instrucciones para compartir ubicación:*\n\n1️⃣ Toca el botón 📎 (clip) en WhatsApp\n2️⃣ Selecciona *Ubicación*\n3️⃣ Elige *Ubicación actual*\n4️⃣ Envía tu ubicación\n\n⏰ Tienes 2 minutos para enviarla, después se registrará sin ubicación."

                success = self._send_whatsapp_message(wa_account, phone_number, message)

            if success:
                print(f"✅ Instrucciones de ubicación enviadas exitosamente")
                return True
            else:
                print(f"❌ Error enviando instrucciones de ubicación")
                return False

        except Exception as e:
            print(f"❌ Error enviando instrucciones de ubicación: {e}")
            _logger.error("Error enviando instrucciones de ubicación: %s", e)
            return False

    def _process_no_location_choice(self, phone_number):
        """
        Procesa cuando el usuario elige registrar asistencia sin ubicación
        """
        try:
            print(f"✅ Procesando elección de registrar sin ubicación para {phone_number}")

            # Obtener solicitud pendiente
            pending_key = f'whatsapp_attendance_pending_{phone_number}'
            pending_data = request.env['ir.config_parameter'].sudo().get_param(pending_key)

            if not pending_data:
                print(f"⚠️ No hay solicitud de asistencia pendiente para {phone_number}")
                self._send_error_message(phone_number, "No hay registro de asistencia pendiente")
                return False

            # Parsear datos pendientes
            employee_id, attendance_type = pending_data.split('|')
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))

            if not employee.exists():
                print(f"❌ Empleado no encontrado: {employee_id}")
                return False

            print(f"👤 Registrando asistencia sin ubicación para {employee.name}")

            # Limpiar solicitud pendiente
            request.env['ir.config_parameter'].sudo().set_param(pending_key, False)

            # Registrar asistencia sin ubicación
            self._register_attendance_without_location(employee, attendance_type, phone_number)

            return True

        except Exception as e:
            print(f"❌ Error procesando elección sin ubicación: {e}")
            _logger.error("Error procesando elección sin ubicación: %s", e)
            return False

    def _process_share_location_choice(self, phone_number):
        """
        Procesa cuando el usuario elige registrar asistencia CON ubicación.
        NUEVA FUNCIONALIDAD: Registra la asistencia inmediatamente y luego pide la ubicación
        para añadirla al registro ya creado.
        """
        try:
            print(f"📍 Procesando elección de registrar CON ubicación para {phone_number}")

            # Obtener solicitud pendiente
            pending_key = f'whatsapp_attendance_pending_{phone_number}'
            pending_data = request.env['ir.config_parameter'].sudo().get_param(pending_key)

            if not pending_data:
                print(f"⚠️ No hay solicitud de asistencia pendiente para {phone_number}")
                self._send_error_message(phone_number, "No hay registro de asistencia pendiente")
                return False

            # Parsear datos pendientes
            employee_id, attendance_type = pending_data.split('|')
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))

            if not employee.exists():
                print(f"❌ Empleado no encontrado: {employee_id}")
                return False

            print(f"👤 Registrando asistencia INMEDIATAMENTE para {employee.name}")

            # 1. REGISTRAR ASISTENCIA INMEDIATAMENTE
            validation_result = self._validate_attendance_state(employee, attendance_type)
            if not validation_result['valid']:
                print(f"❌ Validación fallida: {validation_result['message']}")
                self._send_error_message(phone_number, validation_result['message'])
                # Limpiar solicitud pendiente
                request.env['ir.config_parameter'].sudo().set_param(pending_key, False)
                return False

            # Registrar la asistencia SIN ubicación primero
            attendance_result = self._register_attendance(employee, attendance_type, validation_result)

            if not attendance_result:
                print(f"❌ Error al registrar asistencia")
                self._send_error_message(phone_number, "Error al registrar asistencia")
                # Limpiar solicitud pendiente
                request.env['ir.config_parameter'].sudo().set_param(pending_key, False)
                return False

            print(f"✅ Asistencia registrada inmediatamente - ID: {attendance_result.id}")

            # 2. ENVIAR CONFIRMACIÓN DE REGISTRO
            action_text = "entrada" if attendance_type == 'check_in' else "salida"
            self._send_confirmation_message(phone_number, attendance_type, employee)

            # 3. ACTUALIZAR DATOS PENDIENTES CON EL ID DE LA ASISTENCIA REGISTRADA
            # Ahora guardamos también el ID de la asistencia para poder actualizarla después
            request.env['ir.config_parameter'].sudo().set_param(
                f'whatsapp_attendance_pending_{phone_number}',
                f'{employee.id}|{attendance_type}|{attendance_result.id}'
            )

            # 4. ENVIAR INSTRUCCIONES PARA COMPARTIR UBICACIÓN
            print(f"📍 Enviando instrucciones para añadir ubicación al registro {attendance_result.id}")

            # Buscar la cuenta de WhatsApp activa
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)

            if wa_account:
                location_message = f"📍 Tu {action_text} ya está registrada ✅\n\nAhora puedes enviar tu ubicación para completar el registro.\n\n*Instrucciones:*\n1️⃣ Toca el botón 📎 (clip)\n2️⃣ Selecciona *Ubicación* \n3️⃣ Elige *Ubicación actual*\n4️⃣ Envía tu ubicación\n\n⏰ Tienes 3 minutos para enviarla."

                success = self._send_whatsapp_message(wa_account, phone_number, location_message)

                if success:
                    print(f"✅ Instrucciones de ubicación enviadas exitosamente")
                else:
                    print(f"⚠️ Error enviando instrucciones, pero asistencia ya registrada")

            return True

        except Exception as e:
            print(f"❌ Error procesando elección con ubicación: {e}")
            _logger.error("Error procesando elección con ubicación: %s", e)
            return False

    def _get_location_instruction_template(self):
        """
        Obtiene el nombre de la plantilla de WhatsApp para instrucciones de ubicación
        """
        try:
            # Buscar configuración de plantilla de instrucciones
            config = request.env['ir.config_parameter'].sudo()
            template_name = config.get_param('whatsapp_attendance.location_instruction_template')

            if template_name:
                print(f"📋 Plantilla de instrucciones configurada: {template_name}")
                return template_name
            else:
                print(f"⚠️ No hay plantilla de instrucciones configurada")
                return None

        except Exception as e:
            print(f"❌ Error obteniendo plantilla de instrucciones: {e}")
            return None

    def _validate_attendance_state(self, employee, attendance_type):
        """
        Valida si el empleado puede registrar el tipo de asistencia solicitado.
        Para check_out: busca cualquier entrada sin salida de cualquier día (no solo el actual)
        Para check_in: verifica que no tenga una entrada activa sin salida
        """
        try:
            print(f"🔍 Validando estado de asistencia para {employee.name}")
            print(f"   Tipo solicitado: {attendance_type}")
            print(f"   Estado actual: {employee.attendance_state}")

            if attendance_type == 'check_in':
                # Para entrada: verificar que no tenga entrada activa sin salida de cualquier día
                open_attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if open_attendance:
                    check_in_date = open_attendance.check_in.strftime('%d/%m/%Y %H:%M')
                    print(f"❌ Ya tiene entrada activa desde: {check_in_date}")
                    return {
                        'valid': False,
                        'message': f"Ya tienes una entrada registrada desde el {check_in_date}. Debes registrar salida primero."
                    }

                print(f"✅ Puede registrar entrada")
                return {
                    'valid': True,
                    'message': 'Entrada autorizada'
                }

            elif attendance_type == 'check_out':
                # Para salida: buscar cualquier entrada sin salida (de cualquier día)
                open_attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if not open_attendance:
                    print(f"❌ No hay entrada activa para registrar salida")
                    return {
                        'valid': False,
                        'message': "No tienes ninguna entrada registrada pendiente de salida."
                    }

                # Mostrar información de la entrada encontrada
                check_in_date = open_attendance.check_in.strftime('%d/%m/%Y')
                check_in_time = open_attendance.check_in.strftime('%H:%M')
                today = datetime.now().strftime('%d/%m/%Y')

                if check_in_date == today:
                    print(f"✅ Entrada encontrada del mismo día: {check_in_time}")
                else:
                    print(f"✅ Entrada encontrada de día anterior: {check_in_date} a las {check_in_time}")

                return {
                    'valid': True,
                    'message': f'Salida autorizada para entrada del {check_in_date}',
                    'open_attendance': open_attendance
                }

            return {
                'valid': False,
                'message': 'Tipo de asistencia no válido'
            }

        except Exception as e:
            print(f"❌ Error validando estado de asistencia: {e}")
            _logger.error("Error validando estado de asistencia: %s", e)
            return {
                'valid': False,
                'message': 'Error interno al validar asistencia'
            }

    def _send_attendance_report(self, phone_number, employee):
        """
        Genera y envía un archivo TXT con las últimas 30 asistencias del empleado por WhatsApp
        """
        try:
            # Buscar las últimas 30 asistencias
            attendances = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id)
            ], order='check_in desc', limit=30)

            if not attendances:
                self._send_error_message(phone_number, "No se encontraron asistencias para este empleado.")
                return

            # Generar contenido TXT
            lines = [
                f"Reporte de Asistencias para {employee.name}",
                f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                "",
                "Fecha Entrada | Hora Entrada | Fecha Salida | Hora Salida"
                "\n----------------------------------------------------------"
            ]
            for att in attendances:
                check_in = att.check_in.strftime('%d/%m/%Y|%H:%M') if att.check_in else '--|--'
                check_out = att.check_out.strftime('%d/%m/%Y|%H:%M') if att.check_out else '--|--'
                lines.append(f"{check_in} | {check_out}")
            content = '\n'.join(lines)

            # Guardar archivo temporal
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Enviar archivo por WhatsApp
            self._send_whatsapp_file(phone_number, tmp_path, filename=f"asistencias_{employee.id}.txt")
        except Exception as e:
            print(f"❌ Error generando o enviando reporte de asistencias: {e}")
            self._send_error_message(phone_number, "Error interno al generar el reporte de asistencias.")

    def _send_whatsapp_file(self, phone_number, file_path, filename=None):
        """
        Envía un archivo (documento) por WhatsApp usando la API
        """
        try:
            import requests
            wa_account = request.env['whatsapp.account'].sudo().search([
                ('active', '=', True)
            ], limit=1)
            if not wa_account:
                print(f"❌ No se encontró cuenta de WhatsApp activa")
                return False
            access_token = None
            token_fields = ['access_token', 'token', 'app_secret', 'permanent_access_token']
            for field in token_fields:
                if hasattr(wa_account, field):
                    token_value = getattr(wa_account, field)
                    if token_value:
                        access_token = token_value
                        break
            if not access_token:
                print(f"❌ No se encontró token de acceso en la cuenta de WhatsApp")
                return False
            clean_phone = phone_number.lstrip('+')
            # 1. Subir el archivo a la API de WhatsApp para obtener media_id
            media_url = f"https://graph.facebook.com/v18.0/{wa_account.phone_uid}/media"
            headers_upload = {
                'Authorization': f'Bearer {access_token}'
            }
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename or 'asistencias.txt', f, 'text/plain')
                }
                data_upload = {
                    'messaging_product': 'whatsapp'
                }
                response_upload = requests.post(media_url, headers=headers_upload, files=files, data=data_upload)
            print(f"📤 Respuesta API subida archivo: {response_upload.status_code}")
            print(f"📄 Contenido subida: {response_upload.text}")
            if response_upload.status_code != 200:
                print(f"❌ Error subiendo archivo a WhatsApp")
                return False
            media_id = response_upload.json().get('id')
            if not media_id:
                print(f"❌ No se obtuvo media_id tras subir el archivo")
                return False
            # 2. Enviar el mensaje de documento usando el media_id
            url = f"https://graph.facebook.com/v18.0/{wa_account.phone_uid}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'messaging_product': 'whatsapp',
                'to': clean_phone,
                'type': 'document',
                'document': {
                    'id': media_id,
                    'filename': filename or 'asistencias.txt',
                    'caption': 'Reporte de asistencias'
                }
            }
            response = requests.post(url, headers=headers, json=data)
            print(f"📨 Respuesta API archivo: {response.status_code}")
            print(f"📄 Contenido: {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error enviando archivo por WhatsApp: {e}")
            return False

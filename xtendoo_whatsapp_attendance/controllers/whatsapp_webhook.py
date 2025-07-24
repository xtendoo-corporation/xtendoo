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
        Registra la asistencia del empleado
        """
        try:
            print(f"📝 Registrando asistencia: {attendance_type} para {employee.name}")

            # Buscar si ya tiene una asistencia abierta hoy
            today = datetime.now().date()
            existing_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', f"{today} 00:00:00"),
                ('check_out', '=', False)
            ], limit=1)

            if attendance_type == 'check_in':
                if existing_attendance:
                    print(f"⚠️ El empleado ya tiene una entrada registrada hoy")
                    return False

                # Crear nueva entrada
                attendance = request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': datetime.now(),
                })
                print(f"✅ Entrada registrada - ID: {attendance.id}")
                return attendance

            elif attendance_type == 'check_out':
                if not existing_attendance:
                    print(f"⚠️ No se encontró entrada previa para registrar salida")
                    return False

                # Actualizar con la salida
                existing_attendance.sudo().write({
                    'check_out': datetime.now()
                })
                print(f"✅ Salida registrada - ID: {existing_attendance.id}")
                return existing_attendance

            return False

        except Exception as e:
            print(f"❌ Error registrando asistencia: {e}")
            _logger.error("Error registrando asistencia: %s", e)
            return False

    def _send_confirmation_message(self, phone_number, attendance_type, employee):
        """
        Envía mensaje de confirmación al empleado (funcionalidad futura)
        """
        action_text = "entrada" if attendance_type == 'check_in' else "salida"
        time_now = datetime.now().strftime("%H:%M")

        print(f"📤 [FUTURO] Enviar confirmación a {phone_number}:")
        print(f"    '✅ {employee.name}, tu {action_text} ha sido registrada a las {time_now}'")

    def _send_error_message(self, phone_number, error_message):
        """
        Envía mensaje de error al remitente (funcionalidad futura)
        """
        print(f"📤 [FUTURO] Enviar error a {phone_number}: '{error_message}'")

    @http.route('/whatsapp/webhook/', methods=['GET'], type="http", auth="public", csrf=False)
    def webhookget(self, **kwargs):
        """
        Método heredado que verifica el webhook y muestra toda la información recibida.
        Añade logs detallados para debugging y seguimiento de asistencia.
        """
        print("="*80)
        print("XTENDOO WHATSAPP ATTENDANCE - WEBHOOK GET REQUEST")
        print("="*80)

        # Mostrar información de la petición HTTP
        print(f"Método HTTP: {request.httprequest.method}")
        print(f"URL completa: {request.httprequest.url}")
        print(f"Ruta: {request.httprequest.path}")
        print(f"Query string: {request.httprequest.query_string.decode()}")

        # Mostrar headers de la petición
        print("\n--- HEADERS DE LA PETICIÓN ---")
        for header_name, header_value in request.httprequest.headers.items():
            print(f"{header_name}: {header_value}")

        # Mostrar todos los parámetros recibidos
        print("\n--- PARÁMETROS RECIBIDOS (kwargs) ---")
        for key, value in kwargs.items():
            print(f"{key}: {value}")

        # Extraer parámetros específicos del webhook
        token = kwargs.get('hub.verify_token')
        mode = kwargs.get('hub.mode')
        challenge = kwargs.get('hub.challenge')

        print("\n--- PARÁMETROS DEL WEBHOOK ---")
        print(f"Token de verificación: {token}")
        print(f"Modo: {mode}")
        print(f"Challenge: {challenge}")

        # Información del entorno de Odoo
        print("\n--- INFORMACIÓN DEL ENTORNO ---")
        print(f"Base de datos: {request.env.cr.dbname}")
        print(f"Usuario: {request.env.user.name if request.env.user else 'Sin usuario'}")

        # Validación de parámetros requeridos
        if not (token and mode and challenge):
            print("\n❌ ERROR: Faltan parámetros requeridos (token, mode o challenge)")
            print("Retornando Forbidden()")
            print("="*80)
            return Forbidden()

        # Buscar cuenta de WhatsApp
        print(f"\n--- BÚSQUEDA DE CUENTA WHATSAPP ---")
        print(f"Buscando cuenta con webhook_verify_token: {token}")

        wa_account = request.env['whatsapp.account'].sudo().search([
            ('webhook_verify_token', '=', token)
        ])

        print(f"Cuentas encontradas: {len(wa_account)}")
        if wa_account:
            for account in wa_account:
                print(f"  - ID: {account.id}, Nombre: {account.name}")
                print(f"  - Account UID: {account.account_uid}")
                print(f"  - Phone UID: {account.phone_uid}")

        # Verificación del modo subscribe
        if mode == 'subscribe' and wa_account:
            print("\n✅ VERIFICACIÓN EXITOSA")
            print(f"Modo es 'subscribe' y cuenta encontrada")
            print(f"Retornando challenge: {challenge}")

            response = request.make_response(challenge)
            response.status_code = HTTPStatus.OK

            print(f"Response status: {response.status_code}")
            print("="*80)
            return response

        # Si llegamos aquí, la verificación falló
        print("\n❌ VERIFICACIÓN FALLIDA")
        if mode != 'subscribe':
            print(f"Modo incorrecto: {mode} (esperado: subscribe)")
        if not wa_account:
            print("No se encontró cuenta de WhatsApp con el token proporcionado")

        response = request.make_response({})
        response.status_code = HTTPStatus.FORBIDDEN

        print(f"Response status: {response.status_code}")
        print("="*80)

        return response

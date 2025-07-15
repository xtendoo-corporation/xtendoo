import logging
import json
from http import HTTPStatus
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.whatsapp.controller.main import Webhook

_logger = logging.getLogger(__name__)


class WhatsAppAttendanceWebhook(Webhook):
    """
    Controlador que hereda de Webhook para mostrar información detallada
    de las peticiones recibidas en el webhook de WhatsApp
    """

    @http.route('/whatsapp/webhook/', methods=['POST'], type="json", auth="public")
    def webhookpost(self):
        """
        Método heredado que procesa mensajes de WhatsApp y muestra toda la información recibida.
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

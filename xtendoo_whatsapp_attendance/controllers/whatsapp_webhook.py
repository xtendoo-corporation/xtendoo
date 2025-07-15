import logging
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

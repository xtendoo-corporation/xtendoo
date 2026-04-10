# -*- coding: utf-8 -*-
{
    "name": "Xtendoo Cash Drawer",
    "version": "19.0.3.0.0",
    "category": "Point of Sale",
    "summary": "Cajón portamonedas vía bridge local: apertura a través del proxy Odoo (sin CORS)",
    "description": """
        Módulo para configurar y controlar el cajón portamonedas en el TPV de Odoo.

        Arquitectura: frontend POS → proxy Odoo → bridge local
        -------------------------------------------------------
        La apertura del cajón se realiza a través del proxy integrado en Odoo:
          1. El navegador del TPV llama a POST /xtendoo_cash_drawer/open (mismo origen → sin CORS).
          2. Odoo (Python) reenvía la petición GET al bridge por IP LAN (servidor-a-servidor → sin CORS).

        Esto resuelve definitivamente el problema CORS que surge cuando el bridge local
        (ejecutable en Windows/Linux del cajero) no puede añadir cabeceras CORS porque
        es un binario externo que no se puede modificar.

        El bridge NO necesita configurar cabeceras CORS con esta arquitectura.

        Configuración por TPV:
        - Habilitar bridge local
        - URL del bridge (p.ej. http://192.168.18.7:3210)
        - Nombre de la impresora (parámetro ?printer= enviado al bridge)
        - API Key del bridge (cabecera x-api-key)
        - Apertura automática en pagos en efectivo

        API esperada del bridge (llamada desde Odoo Python, no desde el navegador):
          GET /open-drawer?printer=<nombre>  → { "ok": true }
          GET /health                        → { "status": "ok" }
          Header: x-api-key: <api_key>       (si el bridge requiere autenticación)
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_cash_drawer/static/src/js/cash_drawer_utils.js",
            "xtendoo_cash_drawer/static/src/js/cash_drawer_backend_test.js",
        ],
        "point_of_sale._assets_pos": [
            "xtendoo_cash_drawer/static/src/js/cash_drawer_utils.js",
            "xtendoo_cash_drawer/static/src/js/cash_drawer_button.js",
            "xtendoo_cash_drawer/static/src/js/cash_drawer_navbar_button.js",
            "xtendoo_cash_drawer/static/src/js/cash_drawer_payment.js",
            "xtendoo_cash_drawer/static/src/xml/cash_drawer.xml",
            "xtendoo_cash_drawer/static/src/xml/cash_drawer_navbar.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

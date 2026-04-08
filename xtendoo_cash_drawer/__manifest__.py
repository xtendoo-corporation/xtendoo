# -*- coding: utf-8 -*-
{
    "name": "Xtendoo Cash Drawer",
    "version": "19.0.2.0.0",
    "category": "Point of Sale",
    "summary": "Cajón portamonedas vía bridge local: apertura directa desde el navegador del TPV",
    "description": """
        Módulo para configurar y controlar el cajón portamonedas en el TPV de Odoo.

        Arquitectura: frontend POS → bridge local
        -----------------------------------------
        La apertura del cajón se realiza DIRECTAMENTE desde el navegador del TPV
        mediante fetch() al bridge local (por defecto http://127.0.0.1:3211).
        Odoo no actúa como proxy: no se realizan peticiones Python al cajón.

        Esto resuelve el problema fundamental de los entornos cloud/Docker:
        el bridge corre en el PC del cajero o en la LAN local del cliente,
        no en el servidor Odoo.

        Configuración por TPV:
        - Habilitar bridge local
        - URL del bridge (por defecto http://127.0.0.1:3211 o IP LAN)
        - Nombre de la impresora (parámetro ?printer= enviado al bridge)
        - API Key del bridge (cabecera x-api-key)
        - Apertura automática en pagos en efectivo

        Compatibilidad: el campo legacy cash_drawer_open_url se mantiene
        para instalaciones anteriores que usaban el proxy backend.

        API esperada del bridge:
          GET /open-drawer?printer=<nombre>  → { "ok": true }
          GET /health                        → { "status": "ok" }
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

# -*- coding: utf-8 -*-
{
    "name": "Xtendoo Cash Drawer",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Configuración del cajón portamonedas: impresora y URL de apertura",
    "description": """
        Módulo para configurar el cajón portamonedas en el TPV de Odoo.

        Permite definir, por cada terminal de punto de venta:
        - El nombre exacto de la impresora conectada al cajón.
        - La URL utilizada para enviar la orden de apertura del cajón.
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
            "xtendoo_cash_drawer/static/src/xml/cash_drawer.xml",
            "xtendoo_cash_drawer/static/src/xml/cash_drawer_navbar.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}


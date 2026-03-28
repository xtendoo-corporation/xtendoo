# -*- coding: utf-8 -*-
{
    "name": "Cash Drawer Settings",
    "version": "19.0.3.0.0",
    "category": "Point of Sale",
    "summary": "Apertura del cajón portamonedas mediante impresión dummy en el TPV",
    "description": """
        Abre el cajón portamonedas provocando una impresión mínima (dummy) en la
        impresora de tickets configurada en el TPV.

        Filosofía:
        - No usa comandos directos de hardware desde el navegador.
        - No requiere IoT Box, proxy local ni WebUSB.
        - La apertura del cajón la realiza la impresora como consecuencia natural
          de recibir una impresión, si está configurada para ello.
        - Reutiliza el flujo estándar de impresión del POS de Odoo 19.

        Características:
        * Botón "Abrir cajón portamonedas" en el menú del TPV (hamburguesa).
        * Configuración en pos.config para activar/desactivar la estrategia dummy.
        * Texto configurable para el ticket dummy (mínimo por defecto).
        * Feedback visual de éxito o error amigable.
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
        "point_of_sale._assets_pos": [
            "cash_drawer_settings/static/src/js/pos_config.js",
            "cash_drawer_settings/static/src/js/cash_drawer_button.js",
            "cash_drawer_settings/static/src/xml/cash_drawer.xml",
        ],
        "point_of_sale.assets_tests": [
            "cash_drawer_settings/static/tests/tours/cash_drawer_tour.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

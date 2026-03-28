# -*- coding: utf-8 -*-
{
    "name": "Cash Drawer Settings",
    "version": "19.0.2.0.0",
    "category": "Point of Sale",
    "summary": "Apertura del cajón portamonedas desde Ajustes y desde el botón del TPV",
    "description": """
        Configura y abre el cajón portamonedas tanto desde el menú de Ajustes
        como directamente desde el TPV (Punto de Venta).

        Características:
        * Sección en Ajustes para configurar la impresora y los bytes del comando.
        * Botón en el menú del TPV (hamburguesa) para abrir el cajón.
        * Cascada de estrategias:
            1. Hardware Proxy / IoT Box (mecanismo nativo de Odoo)
            2. WebUSB (experimental, Chrome/Edge, impresora USB local)
            3. Proxy local (script Python en localhost:7070, útil en Windows)
            4. RPC al backend (TCP socket / CUPS / dispositivo directo)
        * Soporte de impresoras de red (TCP IP:puerto) y USB.
        * Compatible con Windows (win32print, copy /b) y Linux (CUPS, /dev/).
        * Tests unitarios Python y tour JS incluidos.
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["base_setup", "point_of_sale"],
    "data": [
        "views/cash_drawer_settings_views.xml",
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "cash_drawer_settings/static/src/js/webusb_printer.js",
            "cash_drawer_settings/static/src/js/cash_drawer_button.js",
            "cash_drawer_settings/static/src/xml/cash_drawer_navbar.xml",
        ],
        "point_of_sale.assets_tests": [
            "cash_drawer_settings/static/tests/tours/cash_drawer_tour.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "POS Serial Scale - Web Serial API",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Integración de balanza por puerto serie usando Web Serial API en el POS",
    "description": """
        Permite conectar una balanza por puerto serie (COM) al POS de Odoo
        usando la Web Serial API del navegador.

        Características:
        - Conexión a balanza por puerto serie (Windows COM7, Linux /dev/ttyUSB0, etc.)
        - Botón de conexión/desconexión en el POS
        - Configuración de parámetros serie (baudRate, dataBits, stopBits, parity, flowControl)
        - Lectura de peso con regex configurable
        - Popup para leer y aplicar peso a productos
        - Integración con productos "a pesar" del POS

        Requisitos:
        - Chrome/Edge/Chromium (Web Serial API)
        - HTTPS o localhost
    """,
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_pos_serial_scale/static/src/js/serial_scale_service.js",
            "xtendoo_pos_serial_scale/static/src/js/serial_scale_popup.js",
            "xtendoo_pos_serial_scale/static/src/js/serial_scale_button.js",
            "xtendoo_pos_serial_scale/static/src/js/pos_store_patch.js",
            "xtendoo_pos_serial_scale/static/src/xml/serial_scale_popup.xml",
            "xtendoo_pos_serial_scale/static/src/xml/serial_scale_button.xml",
            "xtendoo_pos_serial_scale/static/src/xml/navbar_patch.xml",
            "xtendoo_pos_serial_scale/static/src/scss/serial_scale.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}


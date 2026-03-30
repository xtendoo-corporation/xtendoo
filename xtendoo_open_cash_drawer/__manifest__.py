# -*- coding: utf-8 -*-
{
    "name": "Xtendoo Open Cash Drawer",
    "version": "19.0.5.0.0",
    "category": "Point of Sale",
    "summary": "Apertura directa del cajón portamonedas sin impresión (ESC/POS TCP/USB) con fallback a impresión mínima",
    "description": """
        Abre el cajón portamonedas desde el TPV de Odoo usando la estrategia
        óptima disponible, priorizando siempre la apertura directa sin imprimir
        ningún ticket.

        Estrategias en orden de prioridad:
        1. openCashbox() nativo del dispositivo ePOS (sin impresión).
        2. Comando ESC/POS directo desde el servidor Odoo via TCP o CUPS (sin impresión).
           Requiere configurar "Dirección de la impresora del cajón" en la config del TPV.
        3. Hardware proxy / IoT Box de Odoo (sin impresión).
        4. Impresión dummy mínima como último recurso (solo si está habilitado).

        Las estrategias 1-3 envían únicamente los bytes ESC p al pin del cajón,
        sin generar ni alimentar papel ni realizar ningún corte.
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "report/cash_drawer_report.xml",
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_open_cash_drawer/static/src/js/cash_drawer_receipt.js",
            "xtendoo_open_cash_drawer/static/src/js/cash_drawer_button.js",
            "xtendoo_open_cash_drawer/static/src/xml/cash_drawer.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

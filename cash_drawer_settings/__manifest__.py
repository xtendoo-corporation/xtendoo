# -*- coding: utf-8 -*-
{
    "name": "Cash Drawer Settings",
    "version": "19.0.4.1.0",
    "category": "Point of Sale",
    "summary": "Apertura del cajón portamonedas mediante impresión tradicional en el TPV",
    "description": """
        Abre el cajón portamonedas provocando una impresión mínima en la
        impresora de tickets configurada en el TPV mediante los servicios 
        nativos de punto de venta (Owl Components).

        Filosofía:
        - Usa una plantilla de impresión local en el TPV (Componente de recibo).
        - La apertura del cajón la realiza la impresora como consecuencia natural
          de recibir una impresión en el cliente POS.
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
            "cash_drawer_settings/static/src/js/cash_drawer_receipt.js",
            "cash_drawer_settings/static/src/js/cash_drawer_button.js",
            "cash_drawer_settings/static/src/xml/cash_drawer.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

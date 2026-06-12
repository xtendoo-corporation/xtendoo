# -*- coding: utf-8 -*-

{
    "name": "Transferencias internas",
    "summary": "Escaneo clásico de operaciones de almacén sin interfaz Owl propia",
    "version": "19.0.1.0.0",
    "description": """
MVP backend-first para escaneo de operaciones de stock en Odoo 19.
Permite operar pickings desde una vista clásica usando el handler nativo de códigos de barras.
    """,
    "author": "Xtendoo",
    "company": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "category": "Inventory/Inventory",
    "license": "AGPL-3",
    "depends": [
        "stock",
        "barcodes",
        "barcodes_gs1_nomenclature",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/xtendoo_stock_barcode_data.xml",
        "wizard/stock_barcode_internal_wizard_views.xml",
        "views/xtendoo_stock_barcode_menu.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_stock_barcode/static/src/pda/*.js",
            "xtendoo_stock_barcode/static/src/main_menu/main_menu.js",
            "xtendoo_stock_barcode/static/src/main_menu/main_menu.xml",
            "xtendoo_stock_barcode/static/src/client_action/picking_client_action.js",
            "xtendoo_stock_barcode/static/src/client_action/picking_client_action.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}

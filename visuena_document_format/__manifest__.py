# -*- coding: utf-8 -*-

{
    "name": "visuena_document_format",
    "summary": """Formatos de documentos visueña""",
    "version": "15.0.1.0.0",
    "description": """Formatos de documentos visueña""",
    "author": "Dani Domínguez - Xtendoo",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "category": "Extra Tools",
    "depends": ["base", "sale", 'stock', 'sale_management'],
    "license": "AGPL-3",
    "data": [
        # Ventas
        "views/sale/report_saleorder_document.xml",
        "views/sale/sale_order_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

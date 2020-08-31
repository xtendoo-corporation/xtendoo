# -*- coding: utf-8 -*-

{
    "name": "document_format_dji",
    "summary": """Formatos de documentos Distribuciones Joaquin Infante""",
    "version": "12.0.1.0.0",
    "description": """Formatos de documentos Distribuciones Joaquin Infante""",
    "author": "DDL",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "category": "Extra Tools",
    "depends": ["base", "account", "sale", "web", "stock"],
    "license": "AGPL-3",
    "data": [
        # Cabecera y Pie
        "views/layout/external_layout_clean.xml",
        # Ventas
        "views/sale/report_saleorder_document.xml",
        # Albarán
        "views/delivery/report_delivery_document.xml",
        # Factura
        "views/invoice/report_invoice_document.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

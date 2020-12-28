# -*- coding: utf-8 -*-

{
    "name": "Document Format",
    "summary": """Formatos de documentos entregados por Xtendoo""",
    "version": "13.0.1.0.0",
    "description": """Formatos de documentos entregados por Xtendoo""",
    "author": "DDL",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "category": "Extra Tools",
    "depends": ["base",
                "account",
                "sale",
                "web",
                "stock"],
    "license": "AGPL-3",
    "depends": [
        "stock",
        "stock_picking_report_valued",
    ],
    "data": [
        "views/delivery/delivery_document.xml",
        "views/delivery/delivery_commodity.xml",
        "views/invoice/invoice_document.xml",
        "views/sale/sale_order_document.xml",
    ],
    "installable": True,
    "auto_install": False,
}

# -*- coding: utf-8 -*-

{
    "name": "document_format_xtendoo",
    "summary": """Formatos de documentos Xtendoo""",
    "version": "12.0.1.0.0",
    "description": """Formatos de documentos Xtendoo""",
    "author": "DDL",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "category": "Extra Tools",
    "depends": ["base", "account", "sale", "web", "stock"],
    "license": "AGPL-3",
    "data": [
        "views/layout/external_layout_clean.xml",
        "views/sale/report_saleorder_document.xml",
        "views/invoice/report_invoice_document.xml",
        "views/delivery/report_delivery_document.xml",
        "views/payment/report_payment_receipt_document.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

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
        "views/sale/sale_order_document.xml",
        "views/invoice/invoice_document.xml",
        "views/delivery/delivery_document.xml",
        "views/payment/report_payment_receipt_document.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

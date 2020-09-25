# -*- coding: utf-8 -*-

{
    "name": "document_format_Zoopet",
    "summary": """Formatos de documentos Zoopet""",
    "version": "12.0.1.0.0",
    "description": """Formatos de documentos Zoopet""",
    "author": "DDL",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.com",
    "category": "Extra Tools",
    "depends": [
        "base",
        "account",
        "sale",
        "web",
        "stock",
        "product",
        "sale_global_discount",
    ],
    "license": "AGPL-3",
    "data": [
        # layout
        "views/layout/external_layout_clean.xml",
        # delivery
        "views/delivery/report_delivery_document.xml",
        "views/delivery/report_delivery_document_without_price.xml",
        # sale_order
        "views/sale/report_saleorder_document.xml",
        "views/sale/report_sale_order_document_without_price.xml",
        # Purchase_order
        "views/purchase/report_purchaseorder_document.xml",
        # Invoice
        "views/invoice/report_invoice_document.xml",
        # Product Label
        "views/product_label/paper_format.xml",
        "views/product_label/label_template.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

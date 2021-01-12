# -*- coding: utf-8 -*-

{
    "name": "Document Format",
    "summary": """Formatos de documentos entregados por Xtendoo""",
    "version": "13.0.1.0.0",
    "description": """Formatos de documentos entregados por Xtendoo""",
    "author": "DDL",
    "company": "Xtendoo",
    "website": "http://xtendoo.es",
    "category": "Extra Tools",
    "depends": [
        "base",
        "account",
        "sale",
        "web",
        "stock",
    ],
    "license": "AGPL-3",
    "depends": [
        "stock",
        "stock_picking_report_valued",
        "account_invoice_report_due_list",
        "account_payment_partner",
        "account_invoice_report_grouped_by_picking",
    ],
    "data": [
        "views/stock_picking/stock_picking_view.xml",
        "views/delivery/delivery_document.xml",
        "views/delivery/delivery_commodity.xml",
        "views/invoice/invoice_document.xml",
        "views/invoice/invoice_gruped_by_picking.xml",
        "views/layout/external_layout_clean.xml",
        "views/sale/sale_order_document.xml",
    ],
    "installable": True,
    "auto_install": False,
}

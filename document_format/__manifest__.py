{
    "name": "Document Format",
    "summary": """Formatos de documentos entregados por Xtendoo""",
    "version": "13.0.1.0.0",
    "description": """Formatos de documentos entregados por Xtendoo""",
    "author": "Manuel Calero, Daniel Dominguez",
    "company": "Xtendoo",
    "website": "http://xtendoo.es",
    "category": "Extra Tools",
    "depends": ["base", "account", "sale", "web", "stock", "product",],
    "license": "AGPL-3",
    "depends": [
        "sale",
        "stock",
        "stock_picking_report_valued",
        "product",
        "account",
        "stock_picking_product_barcode_report",
        "account_invoice_report_due_list",
        "account_payment_partner",
        "account_invoice_report_grouped_by_picking",
    ],
    "data": [
        "data/paper_format_label.xml",
        "views/stock_picking/stock_picking_view.xml",
        "views/delivery/delivery_document.xml",
        "views/delivery/delivery_commodity.xml",
        "views/invoice/invoice_document.xml",
        "views/invoice/invoice_dossier.xml",
        "views/invoice/invoice_gruped_by_picking.xml",
        "views/layout/external_layout_clean.xml",
        "views/sale/sale_order_document.xml",
        "views/sale/sale_order_blank_document.xml",
        "views/label/product_label.xml",
        "report/report_label_barcode.xml",
        "report/report_label_barcode_template.xml",
    ],
    "installable": True,
    "auto_install": False,
}

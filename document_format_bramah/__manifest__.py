# -*- coding: utf-8 -*-

{
    'name': 'document_format_bramah',
    'summary': """Formatos de documentos Bramah""",
    'version': '12.0.1.0.0',
    'description': """Formatos de documentos Bramah""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'account',
        'sale',
        'web',
        'stock',
        'mrp',
        'purchase_discount',
        'stock_picking_invoice_link',
        'stock_picking_line_sequence',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/layout/external_layout_clean.xml',
        'views/sale/report_saleorder_document.xml',
        'views/delivery/report_delivery_document.xml',
        'views/invoice/report_invoice_document_email.xml',
        'views/invoice/report_invoice_document_preimpreso.xml',
        'views/purchase/purchase_order_document.xml',
        'views/mrp/mrp_report.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

# -*- coding: utf-8 -*-

{
    'name': 'document_format_hr',
    'summary': """Formatos de documentos HR""",
    'version': '12.0.1.0.0',
    'description': """Formatos de documentos HR""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'account',
        'sale',
        'web',
        'stock'
    ],
    'license': 'AGPL-3',
    'data': [
        'views/report_saleorder_document.xml',
        'views/external_layout_clean.xml',
        'views/report_saleorder_bluetooth.xml',
        'views/report_delivery_document.xml',
        'views/report_delivery_document_bluetooth.xml',
        'views/report_invoice_document.xml',
        'views/report_invoice_bluetooth.xml',
        'views/report_payment_receipt_bluetooth.xml',
        'views/saleorder_promotions.xml',
        'views/report_saleorder_document_without_promotions.xml',
        'views/report_saleorder_document_promotions.xml',
        'views/invoice_promotions.xml',
        'views/report_invoice_document_promotions.xml',
        'views/report_invoice_document_without_promotions.xml',
        'views/delivery_promotions.xml',
        'views/report_delivery_document_promotions.xml',
        'views/report_delivery_document_without_promotions.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

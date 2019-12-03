# -*- coding: utf-8 -*-

{
    'name': 'document_format_Zoopet',
    'summary': """Formatos de documentos Zoopet""",
    'version': '12.0.1.0.0',
    'description': """Formatos de documentos Zoopet""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
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
        'views/report_invoice_document.xml',
        'views/report_delivery_document.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

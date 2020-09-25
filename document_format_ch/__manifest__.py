# -*- coding: utf-8 -*-

{
    'name': 'document_format_ch',
    'summary': """Formatos de documentos CH""",
    'version': '12.0.1.0.0',
    'description': """Formatos de documentos CH""",
    'author': 'Dani-Xtendoo',
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
        #layout
        'views/layout/external_layout_clean.xml',
        #sale
        'views/sale/report_saleorder_document.xml',
        'views/sale/report_saleorder_bluetooth.xml',
        #delivery
        'views/delivery/report_delivery_document.xml',
        'views/delivery/report_delivery_document_bluetooth.xml',
        #invoice
        'views/invoice/report_invoice_document.xml',
        'views/invoice/report_invoice_document_2_discounts.xml',
        'views/invoice/report_invoice_bluetooth.xml',
        #payment
        'views/payment/report_payment_receipt_bluetooth.xml',
        'views/payment/report_payment_receipt.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

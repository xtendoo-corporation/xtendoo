# -*- coding: utf-8 -*-

{
    'name': 'document_format_dis',
    'summary': """Formatos de documentos DIS""",
    'version': '12.0.1.0.0',
    'description': """Formatos de documentos DIS""",
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

        #Cabecera y Pie
        'views/layout/external_layout_clean.xml',

        #Ventas
        'views/sale/report_saleorder_document_without_promotions.xml',
        'views/sale/report_saleorder_document_promotions.xml',
        'views/sale/saleorder_promotions.xml',

        #Ventas Bluetooth
        'views/sale_bluetooth/report_saleorder_bluetooth_without_promotions.xml',
        'views/sale_bluetooth/report_saleorder_bluetooth_with_promotions.xml',
        'views/sale_bluetooth/saleorder_promotions_bluetooth.xml',

        #Albarán
        'views/delivery/report_delivery_document_promotions.xml',
        'views/delivery/report_delivery_document_without_promotions.xml',
        'views/delivery/delivery_promotions.xml',

        #Albarán Bluetooth
        'views/delivery_bluetooth/report_delivery_document_with_promotions_bluetooth.xml',
        'views/delivery_bluetooth/report_delivery_document_without_promotions_bluetooth.xml',
        'views/delivery_bluetooth/delivery_promotions_bluetooth.xml',

        #Factura
        'views/invoice/report_invoice_document_promotions.xml',
        'views/invoice/report_invoice_document_without_promotions.xml',
        'views/invoice/invoice_promotions.xml',

        #Factura Bluetooth
        'views/invoice_bluetooth/report_invoice_document_with_promotions_bluetooth.xml',
        'views/invoice_bluetooth/report_invoice_document_without_promotions_bluetooth.xml',
        'views/invoice_bluetooth/invoice_promotions_bluetooth.xml',

        #Factura Sin promociones
        'views/invoice_without_promotions/invoice_without_promotions.xml',

        #Pagos
        'views/payment/report_payment_receipt.xml',

        #Pagos Bluetooth
        'views/payment_bluetooth/report_payment_receipt_bluetooth.xml',

        #Informe de carga
        'views/workload/stock_picking_report.xml',

        #Compras
        'views/purchase/report_purchase_document.xml'



    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

{
    'name': 'Mail Gateway WhatsApp Sales',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Permite enviar plantillas de WhatsApp desde pedidos de venta',
    'author': 'Xtendoo',
    'license': 'LGPL-3',
    'depends': ['sale', 'mail_gateway_whatsapp_variables'],
    'data': [
        'wizard/sale_whatsapp_composer.xml',
        'views/sale_order.xml',
    ],
}

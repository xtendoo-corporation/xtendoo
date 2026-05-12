{
    'name': "Xtendoo Envia Shipping",
    'summary': "Integración con Envia.com para envíos y seguimiento",
    'description': """
Envía tus paquetes a través de Envia y realiza seguimiento en línea
===================================================================

Envia es un proveedor de soluciones integradas de envío y seguimiento para
negocios de comercio electrónico en crecimiento. Se integra con una gran variedad
de transportistas y plataformas, permitiendo optimizar cada etapa del proceso
de fulfillment, reducir tiempos de manejo y mejorar la experiencia del cliente.
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Inventory/Delivery',
    'version': '17.0.1.0.0',
    'application': True,
    'depends': ['stock_delivery', 'phone_validation'],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_envia.xml',
        'views/delivery_carrier_views.xml',
        'wizard/envia_shipping_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'xtendoo_envia/static/src/components/**/*.js',
            'xtendoo_envia/static/src/components/**/*.xml',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
}


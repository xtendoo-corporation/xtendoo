{
    'name': 'Xtendoo Feria - Nombre de cliente en mesas POS',
    'summary': 'Muestra automáticamente el nombre del cliente en las mesas del restaurante POS',
    'description': """
        Al seleccionar un cliente en un pedido asociado a una mesa,
        el nombre del cliente se muestra automáticamente sobre la mesa
        en la vista de plano del restaurante.
    """,
    'version': '19.0.1.0.0',
    'author': 'Xtendoo',
    'category': 'Point of Sale',
    'depends': ['pos_restaurant'],
    'assets': {
        'point_of_sale._assets_pos': [
            'xtendoo_feria/static/src/**/*',
        ],
    },
    'images': ['static/description/icon.png'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

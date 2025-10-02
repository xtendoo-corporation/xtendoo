{
    'name': 'POS UOM Selection',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Permite seleccionar unidades de medición en el POS',
    'description': """
        Este módulo permite a los usuarios cambiar la unidad de medición
        de los productos directamente desde el punto de venta.
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'depends': ['point_of_sale', 'uom'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'xtendoo_pos_uom_selection/static/src/js/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}


# -*- coding: utf-8 -*-

{
    'name': 'Pos Open Cash Drawer',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'author': 'ErpMstar Solutions',
    'summary': 'Allows you to open cash drawer from product screen.',
    'description': "Allows you to open cash drawer from product screen.",
    'depends': ['point_of_sale'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'em_pos_open_cash_drawer/static/src/**/*',
        ],
    },
    'images': [
        'static/description/product.jpg',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 20,
    'currency': 'EUR',
}

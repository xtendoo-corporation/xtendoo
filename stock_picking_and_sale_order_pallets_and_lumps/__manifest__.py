# -*- coding: utf-8 -*-
{
    'name': 'Stock Picking and Sale Order Pallets and Lupms',
    'summary': """Stock Picking and Sale Order Pallets and Lupms""",
    'version': '17.0.1.1.1',
    'description': """Stock Picking and Sale Order Pallets and Lupms""",
    'author': 'Dani Domínguez',
    'company': 'Xtendoo',
    'website': 'http://xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'stock',
        'delivery',
        'sale',
        'account',
        "base",
        "web",
    ],
    'license': 'AGPL-3',
    'data': [
        'views/stock_picking_view.xml',
        'views/sale_order_view.xml',
        'views/account_invoice_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

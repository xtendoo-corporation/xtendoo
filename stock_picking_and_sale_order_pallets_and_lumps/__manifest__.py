# -*- coding: utf-8 -*-
{
    'name': 'Stock Picking and Sale Order Pallets and Lumps',
    'summary': """Stock Picking and Sale Order Pallets and Lumps""",
    'version': '12.0.1.0.0',
    'description': """Stock Picking and Sale Order Pallets and Lumps""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
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

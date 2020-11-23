# -*- coding: utf-8 -*-

{
    'name': 'hide_purchase_cost_in_so_and_invoice',
    'summary': """Hide purchase_price in sale orders and invoices """,
    'version': '12.0.1.0.0',
    'description': """Hide purchase_price in sale orders and invoices""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'account_invoice_margin',
        'sale_margin'
    ],
    'license': 'AGPL-3',
    'data': [
        'views/stock_move_views.xml',
        'views/sale_order_views.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

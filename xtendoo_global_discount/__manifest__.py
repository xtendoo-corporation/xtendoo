{
    'name': 'Xtendoo Global Discount',
    'version': '18.0.1.0.0',
    'summary': 'Descuento global por cliente aplicado automáticamente en ventas y facturas',
    'author': 'Xtendoo',
    'category': 'Sales',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/res_partner_view.xml',
        'views/product_template_view.xml',
        'views/sale_order_view.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

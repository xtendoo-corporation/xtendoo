{
    'name': 'Xtendoo - Punto Verde',
    'version': '17.0.1.0',
    'category': 'Accounting',
    'summary': 'Gestión de Punto Verde propio en Compras y Ventas',
    'author': 'Xtendoo',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
        'purchase',
        'sale',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

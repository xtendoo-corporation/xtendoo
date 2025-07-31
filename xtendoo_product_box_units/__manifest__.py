# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    'name': 'Product Box Units',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage product box units in sales cycle',
    'description': """
Product Box Units Management
============================

This module adds box units functionality to products and sales process:

* Add 'box_units' field to products
* Add 'boxes' field to sale order lines
* Automatic calculation: boxes * box_units = quantity
* Integration throughout the sales cycle
    """,
    'author': 'Xtendoo Software SLU',
    'website': 'https://xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'product',
        'stock',
        'account',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}

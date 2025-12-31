# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Product Archive Duplicate Name',
    'summary': 'Archive products with duplicate names in product.template',
    'version': '18.0.1.0.0',
    'category': 'Product',
    'author': 'Xtendoo',
    'company': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'product',
    ],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


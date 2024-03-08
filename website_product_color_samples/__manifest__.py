# -*- coding: utf-8 -*-
{
    'name': "Website product color samples",
    'summary': """Display product color samples in product view on website""",
    'description': """Display product color samples in product view on website""",
    'author': 'Odoo Masters',
    'category': 'eCommerce',
    'license': 'AGPL-3',
    "version": "16.0.1.0.0",
    'depends': [
        'sale',
        'website_sale',
    ],
    'data': [
        'views/variants.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_product_color_samples/static/src/css/product_configurator.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}

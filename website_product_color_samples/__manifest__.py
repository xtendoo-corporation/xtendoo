# -*- coding: utf-8 -*-
{
    'name': "Website product color samples",
    'summary': """Display product color samples in product view on website""",
    'description': """Display product color samples in product view on website""",
    'author': 'Odoo Masters',
    'category': 'eCommerce',
    'version': '16.0',
    'depends': [
        'sale',
        'website_sale',
    ],
    'data': [
        'views/templates.xml',
        'views/variant_templates.xml',
        'views/views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'static/src/js/color_samples.js',
            'static/src/scss/color_samples.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}

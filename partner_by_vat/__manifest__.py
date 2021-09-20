# -*- coding: utf-8 -*-
{
    'name': "partner_by_vat",

    'summary': """
        Search Partner by VAT""",

    'description': """
        Search Partner by VAT
    """,

    'author': "Iván Ramos Jiménez",
    'website': "https://ivan.ramos.name",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
}

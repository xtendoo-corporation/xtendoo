# -*- coding: utf-8 -*-
{
    'name': "Tutorial creating security groups",

    'summary': """
        Tutorial about how to create and use security groups""",

    'description': """
        This module is a tutorial in the form of an app. In this app you can find the code to create and use
        security groups in Odoo 13.
    """,

    'author': "Oocademy",
    'website': "http://www.oocademy.com",
    'price': 14.95,
    'currency': 'EUR',
    'category': 'Tutorial',
    'version': '13.0.0.1',
    'license': 'Other proprietary',

    'depends': ['base'],
    'images': [
        'static/description/banner.jpg',
    ],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/user_access_view.xml',
    ],
}
# -*- coding: utf-8 -*-
{
    'name': "Tutorial create classes and widgets",

    'summary': """
        Tutorial about how to write classes and widgets in Odoo""",

    'description': """
        This module is a tutorial in the form of an app. In this app you can find the code to create and use
        JavaScript classes and widgets in Odoo 13.
    """,

    'author': "Oocademy",
    'website': "http://www.oocademy.com",
    'price': 14.95,
    'currency': 'EUR',
    'category': 'Tutorial',
    'version': '13.0.0.1',
    'license': 'Other proprietary',
    'depends': ['base', 'web'],
    'images': [
        'static/description/banner.jpg',
    ],

    'data': [
        'views/assets.xml',
        'views/views.xml'
    ],
    'application': True,
    # Loads the file hello_world.xml as QWeb and uses it to render the view.
    'qweb': [
        'static/src/xml/tutorial_quiz.xml',
    ],

}

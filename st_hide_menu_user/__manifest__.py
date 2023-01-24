# -*- coding: utf-8 -*-
###################################################################################
#
#    Grupo ADAP Solutions Tools
#    Hide Menu for Users
#
###################################################################################

{
    'name': 'Hide Menu for Users',
    'version': '15.0.1.0.1',
    'summary': """ 
            Grupo ADAP Solutions Tools Hide Menu for Users
            .""",
    'description': """ 
            Grupo ADAP Solutions Tools Hide Menu for User
            .""",
    'author': 'Solutions Tools Grupo ADAP',
    'company': 'Solutions Tools Grupo ADAP',
    'maintainer': 'Solutions Tools Grupo ADAP',
    'website': 'https://www.grupoadap.com',
##    'live_test_url': 'https://www.grupoadap.com',
    'images': ['static/description/banner.png'],
    'category': 'Tools',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    'contributors': [
        'Developer <support@grupoadap.com>',
    ],
    'depends': ['base'],
    'data': [
        'views/res_users.xml',
        'views/res_security.xml'
    ],
}

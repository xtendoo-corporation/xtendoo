# -*- coding: utf-8 -*-


{
    'name': 'Base Avaible Pricelist',
    'summary': """Base Partner Avaible Pricelist""",
    'version': '13.0.1.0.0',
    'description': """Base Partner Avaible Pricelist""",
    'author': 'Dani Domínguez',
    'company': 'Xtendoo',
    'website': 'http://xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'product',
    ],
    'license': 'AGPL-3',
    'data': [
        'security/security_pricelist_rules.xml',
        'views/view_users_form_pricelist.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
}

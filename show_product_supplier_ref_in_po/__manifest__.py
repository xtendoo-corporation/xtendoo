# -*- coding: utf-8 -*-

###################################################################################
#
#
#
###################################################################################

{
    'name': 'show product supplier ref in po',
    'summary': """Add the field suppler_ref in purchase order line""",
    'version': '12.0.1.0.0',
    'description': """Add the field suppler_ref in purchase order line""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'purchase'
    ],
    'license': 'AGPL-3',
    'data': [
        'views/purchase_order_form_show_suppler_ref.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

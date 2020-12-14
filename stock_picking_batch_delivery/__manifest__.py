# -*- coding: utf-8 -*-

###################################################################################
#
#
###################################################################################

{
    'name': 'Stock Picking Batch Delivery',
    'summary': """Stock Picking Batch Delivery""",
    'version': '12.0.1.0.0',
    'description': """Stock Picking Batch Delivery""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'stock',
        'delivery'

    ],
    'license': 'AGPL-3',
    'data': [
        'views/views.xml',
        'views/report_picking_batch.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

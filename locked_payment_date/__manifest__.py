# -*- coding: utf-8 -*-
{
    'name': "Locked Payment Date",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "xtendoo",
    'website': "http://www.xtendoo.es",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'account'
    ],

    'data': [
        'views/account_payment.xml',
    ],
}

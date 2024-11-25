# -*- coding: utf-8 -*-
{
    'name': "Split Invoice | Bill | Credit-Debit Note",

    'summary': """Split Invoice | Bill | Credit-Debit Note into two""",

    'description': """
        This module will help you to split a invoice, bill, credit or debit note into two parts.
        For splitting we have three options.
        1. Split by amount percentage.
        2. Split by quantity.
        3. Split by products.
        After the split it creates two new Invoice in draft state and cancel the source Invoice.
        Also maintain the history. 
    """,

    'author': "ErpMstar Solutions",
    'category': 'Accounting/Accounting',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    'installable': True,
    'application': True,
    'images': ['static/description/banner.jpg'],
    'price': 19,
    'currency': 'EUR',
}

# -*- coding: utf-8 -*-

{
    'name': 'Invoice Splitting App',
    'author': 'Edge Technologies',
    'version': '16.0.1.2',
    'live_test_url':'https://youtu.be/NkdmEuLsC1U',
    "images":['static/description/main_screenshot.png'],
    'summary': 'Invoice splitting invoices split invoice line for multiple invoice split line customer invoice separation invoice partial invoice split process vendor bill splitting vendor bills spilt vendor bill line separate vendor bill invoice separation',
    'description': """Invoice splitting app""",
    "license" : "OPL-1",
    'depends': ['base','sale_management','account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoice_split_wizard_views.xml',
    ],
    'qweb' : [],
    'demo': [],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price':18,
    'currency': "EUR",
    'category': 'Accounting',
}

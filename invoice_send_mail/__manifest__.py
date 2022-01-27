# Copyright 2021 Manuel Calero - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Invoice Send Mail',
    'version': '13.0.0.1',
    'category': 'Invoicing',
    'author': 'Manuel Calero',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'summary': 'Invoice Value Dat',
    'depends': [
        'base',
        'sale',
        'account',
    ],
    'data': [
        'views/account_invoice.xml',
        'reports/account_invoice_report_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    "post_init_hook": "post_init_hook",
}

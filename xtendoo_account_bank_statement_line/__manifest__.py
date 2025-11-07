# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Xtendoo Account Bank Statement Line Editor',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'View and edit all fields of account.bank.statement.line with running balance verification',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_bank_statement_line_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}


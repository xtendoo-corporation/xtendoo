# Copyright 2021 Manuel Calero - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Invoice Send Mail Cron',
    'version': '13.0.0.1',
    'category': 'Invoicing',
    'author': 'Manuel Calero',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'summary': 'Account Invoice Send Mail Cron',
    'depends': [
        'base',
        'sale',
        'account',
    ],
    'data': [
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}

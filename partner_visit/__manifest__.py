# Copyright 2019 Watchdog - Miguel Perez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Partner Visit',
    'version': '1.0',
    'category': 'Partner Visit',
    'author': 'Watchdog',
    'website': 'https://www.watchdog.es',
    'license': 'AGPL-3',
    'summary': 'Partner Visit',
    'depends': [
        'base', 'sale',
    ],
    'data': [
        'wizards/wizard_report_partner_visit.xml',
        'security/ir.model.access.csv',
        'views/view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

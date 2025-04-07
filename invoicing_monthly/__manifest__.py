# Copyright 2021 Daniel Domínguez - xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Facturación Mensual',
    'summary': """Facturación Mensual""",
    'version': '13.0.1.0.0',
    'description': """Facturación Mensual""",
    'author': 'Dani Domínguez',
    'company': 'Xtendoo',
    'website': 'http://xtendoo.es',
    'category': 'Invoicing Tools',
    'depends': [
        'account',
        'sale',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}

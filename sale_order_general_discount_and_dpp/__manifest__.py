# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Sale order General Discount and DPP',
    'summary': """general discount and dpp per sale order""",
    'version': '12.0.1.0.0',
    'description': """Add general discount and dpp for the customer for sale orders""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'sale',

    ],
    'data': [
        'views/res_partner.xml',
    ],
}

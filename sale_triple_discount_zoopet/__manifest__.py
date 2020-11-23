# Copyright 2015 ADHOC SA  (http://www.adhoc.com.ar)
# Copyright 2017 - 2019 Alex Comba - Agile Business Group
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-

{
    'name': 'sale_triple_discount_zoopet',
    'summary': """sale Triple discount adaptado a zoopet""",
    'version': '12.0.1.0.0',
    'description': """sale Triple discount adaptado a zoopet""",
    'author': 'Dani-Xtendoo',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'sale_management',
        'account_invoice_triple_discount_zoopet',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/sale_order_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

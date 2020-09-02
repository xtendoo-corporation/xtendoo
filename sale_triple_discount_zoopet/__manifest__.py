# Copyright 2015 ADHOC SA  (http://www.adhoc.com.ar)
# Copyright 2017 - 2019 Alex Comba - Agile Business Group
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'sale_trople_discount_zoopet',
    'summary': """sale Triple discount adaptado a zoopet""",
    'version': '12.0.1.0.0',
    'description': """sale Triple discount adaptado a zoopet""",
    "version": "12.0.1.0.0",
    "category": "Accounting & Finance",
     'author': 'ADHOC SA, '
              'Agile Business Group, '
              'Tecnativa, '
              'Odoo Community Association (OCA)',
              'DDL-xtendoo',
    "license": "AGPL-3",
    "depends": ['sale_management',
        'account_invoice_triple_discount',],
    "data": ["views/sale_order_view.xml",],
    "installable": True,
}

# Copyright 2018 QubiQ (http://www.qubiq.es)
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Account Invoice Supplier Change Price',
    'version': '12.0.1.0.0',
    'category': 'Accounting & Finance',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'summary': 'Select Cost Price',
    'depends': [
        'account',
    ],
    'data': [
        'wizards/wizards_select_sale_price.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
}

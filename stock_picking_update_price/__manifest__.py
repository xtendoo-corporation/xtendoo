# Copyright 2019 Xtendoo - Manuel Calero Solis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Stock Picking Update Price',
    'version': '12.0.1.0.0',
    'category': 'Accounting & Finance',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'summary': 'Stock Picking Update Price',
    'depends': [
        'account',
    ],
    'data': [
        'wizards/wizards_select_sale_price.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
}

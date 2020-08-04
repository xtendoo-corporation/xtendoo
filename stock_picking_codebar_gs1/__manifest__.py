# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Stock Picking Codebar GS1',
    'summary': """Stock Picking Codebar GS1""",
    'version': '12.0.1.0.0',
    'description': """Stock Picking Codebar GS1""",
    'author': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'stock',
        'delivery',
        'stock_barcodes',
        'base_gs1_barcode',
        'web_notify',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

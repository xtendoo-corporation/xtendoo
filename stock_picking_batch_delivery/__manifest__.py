# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Stock Picking Batch Delivery',
    'summary': """Stock Picking Batch Delivery""",
    'version': '13.0.1.0.0',
    'description': """Stock Picking Batch Delivery""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'stock',
        'delivery',
        'stock_picking_report_valued',
        'stock_picking_and_sale_order_pallets_and_lumps',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/views.xml',
        'views/report_picking_batch.xml',
    ],
    'installable': True,
    'auto_install': False,
}

{
    'name': 'xtendoo_pos_receipt',
    'summary': 'Personalización de recibos POS ',
    'version': '19.0.0',
    'author': 'Abraham - Xtendoo',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'l10n_es_pos'],
    'assets': {
        'point_of_sale._assets_pos': [
            'xtendoo_pos_receipt/static/src/css/pos_receipt.scss',
            'xtendoo_pos_receipt/static/src/xml/receipt_templates.xml',
            'xtendoo_pos_receipt/static/src/js/receipt_order.js',
        ],
    },
    'data': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

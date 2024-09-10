{
    'name': 'Stock Picking POS',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Add a custom button to the payment screen in POS',
    'depends': [
        'point_of_sale',
        'stock_account',
        'barcodes',
        'web_editor',
        'digest'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_buttons/static/src/js/*',
            'pos_buttons/static/src/xml/payment_screen_button.xml',
        ]
    },
    'installable': True,
    'application': False,
}

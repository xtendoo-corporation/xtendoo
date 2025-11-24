{
    'name': 'Xtendoo POS Receipt Custom',
    'version': '18.0.1.0',
    'category': 'Point of Sale',
    'summary': 'Personalización de recibos POS para Xtendoo',
    'description': """
        Módulo de personalización para los recibos del POS de Xtendoo.

        Características principales:
        - Personalización del header del recibo
        - Personalización del footer del recibo con mensajes personalizados
        - Estilo tipográfico Courier New para todo el recibo
        - Eliminación del logo de Odoo
        - Compatible con Odoo 18
    """,
    'author': 'Xtendoo',
    'depends': ['point_of_sale', 'l10n_es_pos'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'xtendoo_pos_receipt/static/src/js/orderline_patch.js',
            'xtendoo_pos_receipt/static/src/js/order_receipt.js',
            'xtendoo_pos_receipt/static/src/css/pos_receipt.scss',
            'xtendoo_pos_receipt/static/src/xml/receipt_templates.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}

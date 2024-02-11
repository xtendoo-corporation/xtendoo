{
    "name": "Pos Loyalty Return Voycher",
    "summary": "Use vouchers as payment method in pos orders",
    "category": "Point Of Sale & Sales",
    "version": "16.0.1.0.1",
    "website": "https://github.com/OCA/pos",
    "author": "Odoo Community Association (OCA), Xtendoo",
    "application": False,
    "depends": [
        'point_of_sale',
        'pos_loyalty_redeem_payment',
    ],
    "data": [
        "views/loyalty_card_view.xml",
        "views/res_config_settings_view.xml",
        "views/pos_order_view.xml",
    ],
    "assets": {
        "point_of_sale.assets": [
            "pos_loyalty_return_voucher/static/src/js/models.js",
            "pos_loyalty_return_voucher/static/src/js/PaymentScreen.js",
            "pos_loyalty_return_voucher/static/src/xml/OrderReceipt.xml",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}

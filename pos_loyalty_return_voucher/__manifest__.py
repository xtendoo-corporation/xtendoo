{
    "name": "Pos Loyalty Return Payment",
    "summary": "Use vouchers as payment method in pos orders",
    "category": "Point Of Sale & Sales",
    "version": "16.0.1.0.1",
    "website": "https://github.com/OCA/pos",
    "author": "Odoo Community Association (OCA), Xtendoo",
    "application": False,
    "depends": [
        'pos_loyalty_redeem_payment',
    ],
    "data": [
        "views/pos_config_view.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}

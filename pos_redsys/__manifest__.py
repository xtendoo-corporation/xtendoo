{
    "name": "POS Redsys",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Integrate your POS with a Redsys TPV-PC payment terminal",
    "author": "Xtendoo",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_redsys/static/src/**/*",
        ],
    },
    "installable": True,
}

{
    "name": "POS Default Category",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Set a default category when opening the POS session",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_default_category/static/src/**/*",
        ],
    },
    "installable": True,
}

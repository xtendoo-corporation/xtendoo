# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "POS Custom Name & Price per Line",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Permite definir nombre y precio personalizado por línea en el POS",
    "description": """
        Este módulo extiende el Point of Sale para permitir que ciertos productos
        (marcados con un booleano) soliciten un nombre y precio personalizado
        al añadirlos al pedido.

        El nombre y precio solo afectan a esa línea específica, no al producto original.
    """,
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_note/static/src/js/**/*.js",
            "pos_note/static/src/xml/**/*.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

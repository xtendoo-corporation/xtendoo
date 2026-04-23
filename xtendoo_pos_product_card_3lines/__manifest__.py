# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Xtendoo POS Product Card 3 Lines",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Muestra el nombre del producto en 3 líneas en los botones del POS",
    "description": """
        POS Product Card 3 Lines
        ========================

        Por defecto Odoo muestra el nombre del producto en los botones del TPV
        truncado a 2 líneas, lo que dificulta la lectura de descripciones largas.

        Este módulo amplía el límite a 3 líneas y ajusta los estilos tipográficos
        para mejorar la legibilidad de nombres y descripciones largas.
    """,
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_pos_product_card_3lines/static/src/css/product_card_3lines.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

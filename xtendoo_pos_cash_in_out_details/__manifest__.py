# Copyright 2024 Xtendoo - Guillermo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Money Calculator Pos",
    "summary": "Permite usar la calculadora de billetes/monedas en entrada/salida de efectivo del POS",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_pos_cash_in_out_details/static/src/**/*",
        ],
    },
    "installable": True,
}


# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "POS UoM Selection",
    "summary": "Permite seleccionar unidades de medición en el POS",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "website": "https://www.xtendoo.es",
    "author": "Xtendoo",
    "license": "AGPL-3",
    "depends": ["point_of_sale", "uom"],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_pos_uom_selection/static/src/css/pos_uom_selection.css",
            "xtendoo_pos_uom_selection/static/src/js/models.js",
            "xtendoo_pos_uom_selection/static/src/js/UomSelectionPopup.js",
            "xtendoo_pos_uom_selection/static/src/js/ProductScreen.js",
            "xtendoo_pos_uom_selection/static/src/xml/UomSelectionPopup.xml",
            "xtendoo_pos_uom_selection/static/src/xml/ProductScreen.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}

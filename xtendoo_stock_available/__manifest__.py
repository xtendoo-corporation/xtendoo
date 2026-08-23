# Copyright 2014 Numérigraphe
# Copyright 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
#
# Fork mantenido por Xtendoo desde 2026-08-23: OCA descontinuó este módulo
# en stock-logistics-warehouse a partir de 15.0 (no existe en 16.0 ni
# posteriores). Renombrado con prefijo xtendoo_ para evitar colisión de
# nombre técnico con el módulo OCA original. Se mantiene la autoría/
# licencia original.

{
    "name": "Stock available to promise",
    "version": "16.0.1.0.0",
    "author": "Numérigraphe, Sodexis, Odoo Community Association (OCA), Xtendoo",
    "website": "https://github.com/OCA/stock-logistics-warehouse",
    "development_status": "Production/Stable",
    "category": "Warehouse",
    "depends": ["stock"],
    "license": "AGPL-3",
    "data": [
        "views/product_template_view.xml",
        "views/product_product_view.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}

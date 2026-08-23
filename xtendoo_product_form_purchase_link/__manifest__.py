# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
#
# Fork mantenido por Xtendoo desde 2026-08-23: OCA descontinuó este módulo
# en purchase-workflow a partir de 15.0 (no existe en 16.0 ni posteriores).
# Renombrado con prefijo xtendoo_ para evitar colisión de nombre técnico
# con el módulo OCA original. Se mantiene la autoría/licencia original.

{
    "name": "Product Form Purchase Link",
    "summary": """
        Add an option to display the purchases lines from product""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "development_status": "Beta",
    "maintainers": ["rousseldenis"],
    "author": "ACSONE SA/NV, Odoo Community Association (OCA), Xtendoo",
    "website": "https://github.com/OCA/purchase-workflow",
    "depends": ["purchase"],
    "data": [
        "views/purchase_order_line.xml",
        "views/product_template.xml",
        "views/product_product.xml",
    ],
    "installable": True,
}

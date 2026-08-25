# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
#
# Fork mantenido por Xtendoo desde 2026-08-23: OCA descontinuó este módulo
# en purchase-workflow a partir de 15.0 (no existe en 16.0 ni posteriores).
# Renombrado con prefijo xtendoo_ para evitar colisión de nombre técnico
# con el módulo OCA original. Se mantiene la autoría/licencia original.
{
    "name": "Purchase order line price history",
    "version": "18.0.1.0.0",
    "category": "Purchase Management",
    "author": "Tecnativa, Odoo Community Association (OCA), Xtendoo",
    "website": "https://github.com/OCA/purchase-workflow",
    "license": "AGPL-3",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/xtendoo_purchase_order_line_price_history.xml",
        "views/purchase_views.xml",
    ],
    "installable": True,
}

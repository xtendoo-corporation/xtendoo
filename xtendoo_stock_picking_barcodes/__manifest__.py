# Copyright 2020
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Xtendoo Stock Picking Barcodes",
    "summary": "It provides read barcode on stock operations.",
    "version": "12.0.1.1.2",
    "author": "Xtendoo, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-barcode",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "barcodes",
        "stock",
        'xtendoo_web_notify',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/stock_picking_views.xml',
        'wizard/stock_barcodes_read_views.xml',
    ],
    "installable": True,
}

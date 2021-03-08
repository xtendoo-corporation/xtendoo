# Copyright 2020
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Xtendoo Stock Picking Barcodes",
    "summary": "It provides read barcode on stock operations.",
<<<<<<< HEAD
    "version": "12.0.1.1.2",
    "author": "Xtendoo, "
              "Odoo Community Association (OCA)",
=======
    "version": "13.0.1.1.2",
    "author": "Xtendoo, " "Odoo Community Association (OCA)",
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
    "website": "https://github.com/OCA/stock-logistics-barcode",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "barcodes",
        "stock",
        "xtendoo_web_notify",
        "sale_order_product_default_uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/assets.xml",
        "views/stock_picking_views.xml",
        "wizard/stock_barcodes_read_views.xml",
    ],
    "installable": True,
}

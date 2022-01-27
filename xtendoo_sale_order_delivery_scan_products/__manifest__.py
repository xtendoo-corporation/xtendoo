# Copyright Copyright 2021 Daniel Dominguez, Manuel Calero - https://xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Xtendoo Sale Order Delivery Scan Products",
    "summary": "It provides create a button to access to deliver products and scan it.",
    "version": "13.0.1.0.2",
    "author": "Xtendoo",
    "website": "https://xtendoo.es/",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "web_ir_actions_act_multi",
        "sale_order_delivery_products",
        "xtendoo_stock_picking_barcodes"
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
}

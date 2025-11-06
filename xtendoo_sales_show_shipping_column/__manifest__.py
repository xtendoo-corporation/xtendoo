# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sales Show Shipping Column",
    "summary": "Show shipping address column in sale orders and invoices tree views",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "website": "https://xtendoo.es",
    "author": "Xtendoo",
    "license": "AGPL-3",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}


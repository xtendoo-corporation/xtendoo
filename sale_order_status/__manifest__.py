# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Status",
    "version": "13.0.1.3.6",
    "category": "Sales Management",
    "author": "Xtendoo," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/sale-workflow",
    "license": "AGPL-3",
    "depends": ["sale_stock", "account", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_view.xml",
        "views/sale_order_status_view.xml",
    ],
    "installable": True,
}

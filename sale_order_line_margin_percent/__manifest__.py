# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "Margins Percent in Sales Orders ",
    "version": "1.0",
    "category": "Sales/Sales",
    "description": """
This module adds the 'Margin Percent' on sales order.
    """,
    "depends": ["sale_management", "sale_margin", "product",],
    "demo": ["data/product_demo.xml",],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_oder_line_margin_percent_view.xml",
    ],
}

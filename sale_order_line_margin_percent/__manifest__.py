# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Margins Percent in Sales Orders ",
    "summary": "This module adds the 'Margin Percent' on sales order",
    "version": "13.0.1.0.1",
    "development_status": "Beta",
    "category": "Sales",
    "description": """
This module adds the 'Margin Percent' on sales order.
    """,
    "website": "https://xtendoo.es",
    "author": "Manuel Calero, Xtendoo",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "sale_management",
        "sale_margin",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_oder_line_margin_percent_view.xml",
    ],
}

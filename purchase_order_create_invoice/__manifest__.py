# Copyright 2021 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Order Create Invoice",
    "version": "12.0.1.0.0",
    "summary": "Generate single invoice from purchase orders",
    "author": "Manuel Calero - Xtendoo",
    "website": "https://xtendoo.es",
    "category": "Sales",
    "description": """
        Generate single invoice from multiple purchase order
    """,
    "depends": [
        "sale",
        "sale_management",
        "purchase",
        "account",
        "purchase_discount"
    ],
    "data": [
        "wizard/multiple_purchase_one_invoice_wizard.xml",
        "views/sale_purchase_invoice.xml",
    ],
    "installable": True,
}

# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Product Classification",
    "summary": """
        Module introducing a classification field on product template""",
    "author": "Xtendoo, Dani Domínguez",
    "website": "https://github.com/OCA/product-attribute",
    "category": "Product",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "product",
        "sale"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template.xml",
    ],
    "application": True,
}

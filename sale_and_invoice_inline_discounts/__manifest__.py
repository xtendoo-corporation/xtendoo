# -*- coding: utf-8 -*-

{
    "name": "Sale And Invoice Inline discounts",
    "summary": """Sale And Invoice Inline discounts""",
    "version": "18.0.1.0.1",
    "description": """Sale And Invoice Inline discounts""",
    "author": "Dani Domínguez",
    "company": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "category": "Extra Tools",
    "depends": [
        "sale",
        "contacts",
        "account",
    ],
    "license": "LGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/sale_inline_discount.xml",
        "views/sale_order.xml",
        "views/account_move.xml",
        "views/res_partner.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}

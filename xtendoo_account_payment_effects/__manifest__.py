{
    "name": "Xtendoo Account Payment Effects",
    "summary": "Collection effects (remesas) on customer payments, core Odoo only",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "category": "Accounting",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_payment_remesa_data.xml",
        "views/account_payment_method_line_views.xml",
        "views/account_payment_views.xml",
        "views/account_payment_remesa_views.xml",
        "views/menus.xml",
        "wizard/account_payment_register_views.xml",
        "wizard/xtd_create_payment_remesa_views.xml",
    ],
    "installable": True,
}

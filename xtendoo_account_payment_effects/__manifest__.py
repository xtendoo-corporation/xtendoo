{
    "name": "Xtendoo Account Payment Effects",
    "summary": "Collection effects on customer payments using OCA payment orders and lots",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "category": "Accounting",
    "depends": [
        "account_payment_batch_oca",
        "account_reconcile_oca",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_method_line_views.xml",
        "views/account_payment_views.xml",
        "views/account_payment_order_views.xml",
        "views/account_payment_lot_views.xml",
        "views/account_bank_statement_line_views.xml",
        "views/menus.xml",
        "wizard/account_payment_register_views.xml",
        "wizard/xtd_create_payment_lot_views.xml",
    ],
    "installable": True,
}


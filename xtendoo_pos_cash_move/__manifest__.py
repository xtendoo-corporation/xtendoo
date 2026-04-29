{
    "name": "xtendoo_pos_cash_move",
    "summary": "Movimientos de caja (Cash In / Out) desde el backend para Odoo 19",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "GitHub Copilot",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_bank_statement_line_views.xml",
        "views/pos_cash_move_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}

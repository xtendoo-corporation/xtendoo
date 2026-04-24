# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Xtendoo Account Move AI",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": (
        "Create journal entries from documents (invoices, payslips, expenses) "
        "using AI auto-detection"
    ),
    "depends": [
        "account",
        "base",
        "mail",
        "xtendoo_ai_connector",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "wizards/account_move_ai_wizard_views.xml",
    ],
    "external_dependencies": {
        "python": ["pdf2image"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

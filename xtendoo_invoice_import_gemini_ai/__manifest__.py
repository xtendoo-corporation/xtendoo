# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Invoice Import Gemini AI",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Import vendor invoices using Google Gemini AI",
    "depends": [
        "account",
        "base",
        "mail",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],
    "external_dependencies": {
        "python": ["google-generativeai", "pdf2image"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

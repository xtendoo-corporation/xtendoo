# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Invoice AI - OpenAI Integration",
    "version": "18.0.1.0",
    "category": "Accounting",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Import vendor invoices using OpenAI (ChatGPT) vision and structured extraction",
    "depends": [
        "account",
        "base",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/settings_views.xml",
        "views/account_move_views.xml",
        "views/account_journal_views.xml",
        "views/ai_feedback_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_invoice_ai/static/src/js/notification_handler.js",
            "xtendoo_invoice_ai/static/src/js/invoice_ai_uploader.js",
            "xtendoo_invoice_ai/static/src/js/invoice_list_controller.js",
            "xtendoo_invoice_ai/static/src/xml/invoice_ai_uploader.xml",
        ],
    },
    "external_dependencies": {
        "python": ["openai", "pdf2image", "jsonschema"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

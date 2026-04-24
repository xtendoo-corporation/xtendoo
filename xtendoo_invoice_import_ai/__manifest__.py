{
    "name": "Xtendoo Invoice Import AI",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Import vendor invoices using AI (Gemini, OpenAI, Claude)",
    "depends": [
        "account",
        "analytic",
        "base",
        "mail",
        "xtendoo_ai_connector",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_analytic_line_views.xml",
    ],
    "external_dependencies": {
        "python": ["pdf2image"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

{
    "name": "Xtendoo Purchase Import AI",
    "version": "19.0.1.0.0",
    "category": "Purchase",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Import purchase orders from supplier documents using AI (Gemini, OpenAI, Claude)",
    "depends": [
        "purchase",
        "mail",
        "xtendoo_ai_connector",
        "xtendoo_invoice_import_ai",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "external_dependencies": {
        "python": ["pdf2image"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import invoice_ai_wizard
# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Invoice AI - OpenAI Integration",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "AGPL-3",
    "summary": "Import vendor invoices using OpenAI (ChatGPT) vision and structured extraction",
    "depends": [
        "account",
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/menus.xml",
        "views/wizard_views.xml",
        "views/ai_job_views.xml",
        "views/settings_views.xml",
    ],
    "external_dependencies": {
        "python": ["openai", "pdf2image", "jsonschema"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}


# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Xtendoo AI Connector",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Generic AI connector for Gemini, OpenAI and Anthropic Claude",
    "depends": ["base", "mail"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "external_dependencies": {
        "python": ["google-genai", "openai", "anthropic"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

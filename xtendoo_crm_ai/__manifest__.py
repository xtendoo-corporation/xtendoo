# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Xtendoo CRM AI",
    "version": "19.0.1.0.0",
    "category": "CRM",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Enrich CRM leads/opportunities from free text using AI",
    "depends": [
        "crm",
        "base",
        "mail",
        "xtendoo_ai_connector",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "wizards/crm_lead_ai_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

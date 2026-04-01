{
    "name": "Multi-Company Encapsulate CRM",
    "summary": "Force company_id in CRM Leads and Teams.",
    "description": "Technical module to encapsulate CRM records within the active company.",
    "author": "Xtendoo",
    "category": "Technical",
    "version": "19.0.1.1.0",
    "depends": ["base", "crm", "xtendoo_encapsulate_companies_contacts"],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "data": [
        "security/crm_bypass_rules.xml",
        "views/crm_lead_views.xml",
    ],
    "post_init_hook": "_post_init_hook",
}

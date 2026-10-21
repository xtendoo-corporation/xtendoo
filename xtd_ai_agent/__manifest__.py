{
    "name": "Agente IA",
    "summary": "Asistente de IA integrado en Odoo con queue_job y Claude",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["xtd_ai_gateway", "queue_job"],
    "data": [
        "data/queue_job_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}

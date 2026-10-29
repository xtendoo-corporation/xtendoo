{
    "name": "Agente IA",
    "summary": (
        "Asistente de IA integrado en Odoo: pasarela de seguridad, agente con "
        "Claude y chat"
    ),
    "version": "19.0.2.2.0",
    "category": "Productivity",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["base", "mail", "bus", "web", "queue_job"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
        "data/queue_job_data.xml",
        "views/xtd_ai_audit_views.xml",
        "views/xtd_ai_conversation_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_config_settings_agent_views.xml",
        "views/menus.xml",
        "views/chat_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtd_ai/static/src/js/safe_markdown.esm.js",
            "xtd_ai/static/src/js/chat_service.esm.js",
            "xtd_ai/static/src/js/chat_conversation.esm.js",
            "xtd_ai/static/src/js/chat_window.esm.js",
            "xtd_ai/static/src/js/chat_app.esm.js",
            "xtd_ai/static/src/js/chat_systray.esm.js",
            "xtd_ai/static/src/xml/*.xml",
            "xtd_ai/static/src/scss/*.scss",
        ],
        "web.assets_unit_tests": [
            "xtd_ai/static/tests/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

{
    "name": "Agente IA: pasarela de seguridad",
    "summary": (
        "Barrera de seguridad entre el agente IA y Odoo: permisos del usuario, "
        "solo borradores y auditoría"
    ),
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["base", "mail", "bus"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
        "views/xtd_ai_audit_views.xml",
        "views/xtd_ai_conversation_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

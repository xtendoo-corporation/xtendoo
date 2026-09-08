# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo WhatsApp Onboarding",
    "version": "19.0.1.0.0",
    "category": "Marketing",
    "summary": (
        "Connect a client's WhatsApp Business Account to Odoo "
        "via Meta WhatsApp Embedded Signup"
    ),
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "xtendoo_mail_gateway_whatsapp",
        "web",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/mail_gateway_views.xml",
        "views/whatsapp_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_whatsapp_onboarding/static/src/js/whatsapp_embedded_signup.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}

# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo WhatsApp Embedded Login",
    "version": "18.0.1.0.0",
    "category": "Marketing",
    "summary": "Habilita la coexistencia de WhatsApp mediante Embedded Signup",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": ["mail_gateway_whatsapp", "web"],
    "data": [
        "views/mail_gateway_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_mail_gateway_whatsapp_login/static/src/js/whatsapp_login.js",
        ],
    },
    "installable": True,
}


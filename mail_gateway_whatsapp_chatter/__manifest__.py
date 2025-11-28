# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Gateway WhatsApp - Chatter Integration",
    "version": "18.0.1.0.0",
    "category": "Social",
    "summary": "Add WhatsApp button to chatter for mail_gateway_whatsapp",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "mail_gateway_whatsapp",
        "web",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_gateway_whatsapp_chatter/static/src/chatter/*.js",
            # "mail_gateway_whatsapp_chatter/static/src/chatter/*.xml",
            "mail_gateway_whatsapp_chatter/static/src/components/chatter/*.xml",
            "mail_gateway_whatsapp_chatter/static/src/scss/*.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}

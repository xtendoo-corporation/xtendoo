# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Mail Whatsapp Gateway",
    "summary": """
        Set a gateway for whatsapp""",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Xtendoo, Creu Blanca, Dixmit, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["xtendoo_mail_gateway", "phone_validation", "contacts", "partner_mobile"],
    "external_dependencies": {"python": ["requests_toolbelt"]},
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizards/whatsapp_composer.xml",
        "wizards/mail_compose_gateway_message.xml",
        "views/mail_whatsapp_template_views.xml",
        "views/mail_gateway.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_mail_gateway_whatsapp/static/src/components/**/*",
        ],
    },
}

# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo WhatsApp Webhook Relay",
    "version": "18.0.1.0.0",
    "category": "Marketing",
    "summary": (
        "Relay Meta WhatsApp webhook events to the right client Odoo "
        "instance, for clients onboarded via xtendoo_whatsapp_onboarding"
    ),
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "mail_gateway_whatsapp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/xtendoo_whatsapp_relay_client_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}

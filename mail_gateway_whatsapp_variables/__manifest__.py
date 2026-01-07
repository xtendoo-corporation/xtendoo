# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Gateway WhatsApp - Template Variables",
    "version": "18.0.1.9.0",
    "category": "Social",
    "summary": "Add support for template variables, buttons, attachments and auto-confirmation flow in WhatsApp messages",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "mail_gateway_whatsapp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/whatsapp_menu.xml",
        "views/whatsapp_predefined_templates_action.xml",
        "views/whatsapp_views.xml",
        "views/whatsapp_pending_confirmation_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}


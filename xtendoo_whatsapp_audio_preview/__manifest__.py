# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo WhatsApp Audio Preview",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "summary": "Preview WhatsApp audio attachments directly in Odoo conversations",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "mail",
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_whatsapp_audio_preview/static/src/js/audio_attachment.js",
            "xtendoo_whatsapp_audio_preview/static/src/xml/audio_attachment.xml",
            "xtendoo_whatsapp_audio_preview/static/src/css/audio_attachment.css",
        ],
    },
    "installable": True,
    "application": False,
}

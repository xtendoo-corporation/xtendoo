# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Discuss WhatsApp",
    "version": "19.0.1.0.0",
    "category": "Productivity/Discuss",
    "summary": "WhatsApp-inspired visual theme for Odoo Discuss",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "xtendoo_discuss_whatsapp/static/src/js/message_patch.js",
            "xtendoo_discuss_whatsapp/static/src/scss/discuss_whatsapp.scss",
        ],
        "web.assets_web_dark": [
            "xtendoo_discuss_whatsapp/static/src/scss/discuss_whatsapp.dark.scss",
        ],
    },
    "installable": True,
    "application": False,
}

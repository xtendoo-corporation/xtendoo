# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo PWA Manifest",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "summary": "Customize Odoo's web app manifest for standalone mobile use",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": ["web"],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/webclient_templates.xml",
    ],
    "installable": True,
    "application": False,
}

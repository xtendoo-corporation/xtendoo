# -*- coding: utf-8 -*-
{
    "name": "Xtendoo Xtd Theme",
    "summary": "Personalización visual y debranding del entorno de trabajo Xtd",
    "version": "19.0.1.0.0",
    "author": "Xtendoo SLU",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "category": "Themes/Backend",
    "depends": [
        "web",
        "web_enterprise",
        "disable_odoo_online",
        "mail_debranding",
        "portal_debranding",
    ],
    "data": [
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_xtd_theme/static/src/scss/xtd_theme.scss",
            "xtendoo_xtd_theme/static/src/js/xtd_branding.esm.js",
            "xtendoo_xtd_theme/static/src/xml/error_dialogs.xml",
            "xtendoo_xtd_theme/static/src/xml/res_config_edition.xml",
        ],
        "web.assets_frontend": [
            "xtendoo_xtd_theme/static/src/scss/xtd_theme.scss",
        ],
        "point_of_sale._assets_pos": [
            "xtendoo_xtd_theme/static/src/scss/xtd_pos.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}

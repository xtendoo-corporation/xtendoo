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
        "web_responsive",
        "disable_odoo_online",
        "mail_debranding",
        "portal_debranding",
        "auth_signup",
    ],
    "data": [
        "data/dashboard_data.xml",
        "views/res_users_views.xml",
        "views/webclient_templates.xml",
        "views/dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_xtd_theme/static/src/scss/xtd_theme.scss",
            "xtendoo_xtd_theme/static/src/scss/xtd_menu.scss",
            "xtendoo_xtd_theme/static/src/scss/xtd_sidebar_toggle.scss",
            "xtendoo_xtd_theme/static/src/js/xtd_branding.esm.js",
            "xtendoo_xtd_theme/static/src/js/xtd_navbar_sidebar.esm.js",
            "xtendoo_xtd_theme/static/src/xml/error_dialogs.xml",
            "xtendoo_xtd_theme/static/src/js/xtd_color_scheme.esm.js",
            "xtendoo_xtd_theme/static/src/components/dashboard/dashboard.js",
            "xtendoo_xtd_theme/static/src/xml/xtd_navbar.xml",
            "xtendoo_xtd_theme/static/src/components/dashboard/dashboard.xml",
            "xtendoo_xtd_theme/static/src/components/dashboard/dashboard.scss",
        ],
        "web.assets_frontend": [
            "xtendoo_xtd_theme/static/src/scss/xtd_theme.scss",
            "xtendoo_xtd_theme/static/src/scss/xtd_login.scss",
            "xtendoo_xtd_theme/static/src/xml/user_switch.xml",
        ],
        "web.assets_web_dark": [
            "xtendoo_xtd_theme/static/src/scss/xtd_theme.dark.scss",
            "xtendoo_xtd_theme/static/src/scss/xtd_menu.dark.scss",
        ],
        "point_of_sale._assets_pos": [
            "xtendoo_xtd_theme/static/src/scss/xtd_pos.scss",
        ],
        "web.assets_tests": [
            "xtendoo_xtd_theme/static/tests/tours/xtd_theme_backend_tour.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}

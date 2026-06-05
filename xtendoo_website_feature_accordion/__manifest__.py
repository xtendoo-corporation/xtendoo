# -*- coding: utf-8 -*-
{
    "name": "Website Feature Accordion",
    "summary": "Snippet reutilizable tipo Salesforce: imagen + acordeón interactivo "
               "con cambio de imagen al seleccionar cada elemento.",
    "version": "19.0.1.0.0",
    "author": "Xtendoo SLU",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "category": "Website/Website",
    "depends": [
        "website",
    ],
    "data": [
        "views/snippets/s_feature_accordion.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "xtendoo_website_feature_accordion/static/src/snippets/s_feature_accordion/000.scss",
            "xtendoo_website_feature_accordion/static/src/snippets/s_feature_accordion/feature_accordion.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}

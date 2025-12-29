# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "MIS Report Enhanced Viewer",
    "version": "18.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Modern interactive viewer for MIS Builder reports with Enhanced UX",
    "author": "Xtendoo Corporation",
    "website": "https://xtendoo.es",
    "depends": [
        "web",
        "mis_builder",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mis_report_instance_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_mis_report_viewer/static/src/components/**/*",
            "xtendoo_mis_report_viewer/static/src/scss/mis_viewer.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

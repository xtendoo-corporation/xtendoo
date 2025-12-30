# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "MIS Report Spanish Reports - Quick Access",
    "version": "18.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Quick menu access to Spanish MIS reports (Balance, PyG, PYME)",
    "description": """
        Quick Access to Spanish MIS Reports
        ====================================

        Provides dedicated menu entries for Spanish financial reports:
        - Balance Abreviado (Abbreviated Balance Sheet)
        - Balance Normal (Normal Balance Sheet)
        - PyG Abreviado (Abbreviated P&L)
        - PyG Normal (Normal P&L)
        - Balance PYME (SME Balance Sheet)
        - PyG PYME (SME P&L)

        Features:
        - Automatically creates current year report if it doesn't exist
        - Shows filtered list of reports by type
        - Easy access from Finance menu
    """,
    "author": "Xtendoo Corporation",
    "website": "https://xtendoo.es",
    "depends": [
        "mis_builder",
        "l10n_es_mis_report",
    ],
    "data": [
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}


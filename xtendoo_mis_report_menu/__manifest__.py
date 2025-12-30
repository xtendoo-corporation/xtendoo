# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "MIS Report Spanish Reports - Quick Access",
    "version": "18.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Quick menu access to all Spanish MIS reports (Balance, PyG, PYME, SFL)",
    "description": """
        Quick Access to Spanish MIS Reports
        ====================================

        Provides dedicated menu entries for all Spanish financial reports:

        Balance Sheets:
        - Balance Abreviado (Abbreviated Balance Sheet)
        - Balance Completo (Complete Balance Sheet)
        - Balance PYMES (SME Balance Sheet)
        - Balance PYMESFL (Non-profit SME Balance Sheet)

        Profit & Loss:
        - PyG Abreviado (Abbreviated P&L)
        - PyG Completo (Complete P&L)
        - PyG PYMES (SME P&L)
        - PyG PYMESFL (Non-profit SME P&L)

        Other Reports:
        - Estado de Ingresos y Gastos Reconocidos (Statement of Recognized Income and Expenses)

        Features:
        - Automatically creates current year report if it doesn't exist
        - Shows filtered list of reports by type
        - Easy access from Finance menu
        - Custom styles (gray backgrounds, no italics)
    """,
    "author": "Xtendoo Corporation",
    "website": "https://xtendoo.es",
    "depends": [
        "mis_builder",
        "l10n_es_mis_report",
    ],
    "data": [
        "data/mis_report_styles.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}


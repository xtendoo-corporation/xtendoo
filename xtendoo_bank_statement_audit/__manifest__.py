# -*- coding: utf-8 -*-
# Copyright 2024 Xtendoo - https://xtendoo.es
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Bank Statement Audit',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Auditoría de extractos bancarios con saldo acumulado y exportación Excel',
    'description': """
Bank Statement Audit
====================

Este módulo proporciona una pantalla de auditoría para extractos bancarios que permite:

* Visualizar todos los movimientos de extractos bancarios (account.bank.statement.line)
* Ver el saldo acumulado (running balance) calculado eficientemente con SQL
* Filtrar por diario, partner, fechas, estado de conciliación
* Agrupar por diario, partner o extracto
* Exportar a Excel (XLSX) con todas las columnas visibles
* KPIs con totales del periodo filtrado

El saldo acumulado se calcula:
* Por cada diario de forma independiente
* Ordenado por fecha ascendente y ID
* Usando window functions de SQL para máximo rendimiento
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/export_xlsx_wizard_views.xml',
        'views/bank_statement_audit_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

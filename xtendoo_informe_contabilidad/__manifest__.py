# -*- coding: utf-8 -*-
# Copyright 2024 Xtendoo - https://xtendoo.es
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Informe Contabilidad - Diario de Facturas',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Genera un informe Excel con el diario de facturas de clientes entre dos fechas',
    'description': """
Informe Contabilidad - Diario de Facturas
==========================================
Este módulo proporciona un asistente para generar un informe Excel (XLSX)
con el diario de facturas de clientes con las siguientes columnas:
* Serie: Código del diario contable
* Número de factura: Número de la factura
* Fecha: Fecha de la factura
* Referencia del cliente: Referencia indicada en la factura
* Neto: Importe base imponible (sin IVA)
* Importe de IVA: Importe del IVA
* Total de factura: Importe total (neto + IVA)
Se puede filtrar por rango de fechas y opcionalmente por diario contable.
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
        'wizard/invoice_report_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

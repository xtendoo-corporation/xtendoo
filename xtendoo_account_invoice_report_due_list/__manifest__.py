# Copyright 2018-2021 Tecnativa - Carlos Dauden
# Copyright 2020 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
#
# Fork mantenido por Xtendoo desde 2026-08-24: OCA descontinuó este módulo
# en account-invoice-reporting a partir de 16.0 (no existe en 17.0 ni
# posteriores). Renombrado con prefijo xtendoo_ para evitar colisión de
# nombre técnico con el módulo OCA original. Se mantiene la autoría/
# licencia original.
{
    "name": "Account Invoice Report Due List",
    "summary": "Show multiple due data in invoice",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-invoice-reporting",
    "author": "Tecnativa, Odoo Community Association (OCA), Xtendoo",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account"],
    "data": ["views/account_invoice_view.xml", "views/report_invoice.xml"],
}

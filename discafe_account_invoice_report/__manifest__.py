# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Discafe Account Invoice Report',
    'version' : '1.1',
    'summary': 'Invoices & Payments',
    'sequence': 15,
    'description': """ Discafe Account Invoice Report """,
    'category': 'Invoicing Management',
    'depends' : ['base_setup', 'product', 'analytic', 'portal', 'digest', 'account_invoice_line_report', 'account'],
    'data': [
        'report/account_invoice_report_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

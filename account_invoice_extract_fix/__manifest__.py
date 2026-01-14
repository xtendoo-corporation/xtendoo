# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Invoice Extract Fix',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix for undefined fields error in invoice extract',
    'description': """
Account Invoice Extract Fix
============================

This module fixes a JavaScript error that occurs when using the invoice extract feature
with analytic distribution fields. The error "Cannot read properties of undefined (reading 'fields')"
is resolved by adding proper validation in the getBoxType method.

The fix ensures that when focusing on a field within a x2many relation (like analytic_distribution
in invoice lines), the code properly checks if the parent field exists and has the necessary
configuration before trying to access its fields.
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'depends': [
        'account_invoice_extract',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'account_invoice_extract_fix/static/src/js/invoice_extract_form_fix.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}


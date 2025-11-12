# -*- coding: utf-8 -*-

{
    'name': 'Partner Merge by Email',
    'summary': """Merge duplicate partners with the same email automatically""",
    'version': '18.0.1.0.0',
    'description': """
        This module allows you to merge all duplicate partners that share the same email address
        automatically without asking one by one. It provides a wizard to execute the merge operation
        in batch mode.
    """,
    'author': 'Xtendoo',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Contacts',
    'depends': [
        'base',
        'contacts',
    ],
    'license': 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'wizard/partner_merge_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


{
    'name': "Account Ledger Entries",
    'version': '16.0.1.0.0',
    'summary': """Add menu item to access accounting ledgers""",
    'description': """Add menu item to access accounting ledgers""",
    'author': "Salvador Gonzalez (Xtendoo)",
    'company': "Xtendoo",
    'maintainer': 'Xtendoo',
    'website': "https://xtendoo.es",
    'category': 'Tools',
    'depends': [
        'account',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/account_menuitem.xml',
    ],
    'installable': True,
    'auto_install': False,
}

{
    'name': 'Account Move Sequence Fix',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix sequence id issue when posting account moves',
    'description': """
        This module fixes the issue where the sequence id is passed as a boolean
        instead of an integer when posting account moves, causing PostgreSQL errors.
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}


# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Account Payment Filter Today',
    'version': '12.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Account Payment Filter Today',
    'description': """
Account Payment Filter Today
    """,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
{
    'name': 'avaible_user_create_invoice',
    'summary': """Avaible User Create Invoice""",
    'version': '12.0.1.0.0',
    'description': """Avaible User create Invoice""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'base',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/view_users_form_create_invoice.xml',
    ],
    "depends": [
        'sale',
    ],
    'installable': True,
    'auto_install': True,
}

{
    'name': 'Avaible User Create Invoice',
    'summary': """Avaible User Create Invoice and modify payment date""",
    'version': '12.0.1.0.0',
    'description': """Avaible User create Invoice""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
    ],
    'license': 'AGPL-3',
    'data': [
        'views/view_users_form_create_invoice.xml',
        'views/account_payment.xml',
    ],
    "depends": [
        'sale',
    ],
    'installable': True,
    'auto_install': True,
}

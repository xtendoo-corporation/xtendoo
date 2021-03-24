{
    'name': 'D & HR Administrator',
    'summary': """Administration settings for Discafé and Huelva Regalos""",
    'version': '12.0.1.0.0',
    'description': """Administration settings foR Discafé and Huelva Regalos""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'https://xtendoo.es/',
    'category': 'Admin Tools',
    'depends': [
        'base',
        'sale',
        'product',
        'sale_margin',
        'product',
        'account',
        'account_invoice_margin',
    ],
    'license': 'AGPL-3',
    'data': [
        'security/security.xml',
        'views/sale_order_view_restrict.xml',
        'views/account_payment.xml',
        'views/account_invoice_restrict.xml',
        'views/product_template_restrict.xml',
    ],
    'installable': True,
    'auto_install': True,
}

{
    'name': "Edit Sale Order Date",
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Allow sales users to edit the sale order date',
    'description': 'Sales users can change the quotation and sales order date '
                   'without any additional security group.',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

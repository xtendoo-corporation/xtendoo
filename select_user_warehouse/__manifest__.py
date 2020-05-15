# -*- coding: utf-8 -*-


{
    'name': "Select User Warehouse for Sales",
    'author': 'Xtendoo',
    'category': 'Sales',
    'summary': """Select Warehouse on the Sales order automatically based on Warehouse set at the User""",
    'license': 'AGPL-3',
    'website': 'http://www.xtendoo.es',
    'description': """
""",
    'version': '12.0.0.1',
    'depends': ['base','stock','sale_management'],
    'data': ['views/user_view.xml'],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

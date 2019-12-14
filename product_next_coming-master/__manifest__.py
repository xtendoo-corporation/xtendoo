# -*- coding: utf-8 -*-
#
# command to create :
# docker exec odoo12_odoo_1 /usr/bin/odoo scaffold product_next_coming /usr/lib/python3/dist-packages/odoo/aditional_addons
#
{
    'name': "product_next_coming",

    'summary': """
        Show a column with the date of the next delivery of a product
    """,
    'description': """
        Show a column with the date of the next delivery of a product
    """,

    'author': "Xtendoo",
    'website': "http://www.xtendoo.es",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
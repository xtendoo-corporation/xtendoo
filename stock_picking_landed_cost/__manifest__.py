# -*- coding: utf-8 -*-
#
# command to create :
# docker exec odoo12_odoo_1 /usr/bin/odoo scaffold stock_picking_landed_cost /usr/lib/python3/dist-packages/odoo/aditional_addons
#
{
    'name': "stock_picking_landed_cost",

    'summary': """
        Show a button to access direct from picking to landed cost
    """,
    'description': """
        Show a button to access direct from picking to landed cost
    """,

    'author': "Xtendoo",
    'website': "http://www.xtendoo.es",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'stock',
        'stock_landed_costs'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
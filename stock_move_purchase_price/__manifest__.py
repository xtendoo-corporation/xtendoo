# -*- coding: utf-8 -*-
{
    'name': "stock_move_purchase_price",

    'summary': """
        Módulo para visualizar el precio del pedido en el albarán
    """,

    'description': """
        Módulo para visualizar el precio del pedido en el albarán
    """,

    'author': "Manuel Calero Solís",
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
        'purchase_stock',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/wizards.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
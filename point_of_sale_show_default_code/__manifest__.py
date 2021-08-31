# -*- coding: utf-8 -*-
{
    'name': "point_of_sale_show_default_code",

    'summary': """
        Módulo para visualizar el código del producto en POS
    """,

    'description': """
        Módulo para visualizar el código del producto en POS
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
        'point_of_sale',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/pos.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml'
    ],
}
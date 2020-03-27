# -*- coding: utf-8 -*-


{
    'name': 'Add category pricelist',
    'summary': """Add pricelist to product categories""",
    'version': '12.0.1.0.0',
    'description': """Add pricelist to product categories""",
    'author': 'DDL',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'product',
        'stock'
    ],
    'license': 'AGPL-3',
    'data': [
        'views/category_pricelist_item.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

}

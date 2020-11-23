# Copyright 2020 Xtendoo - DDL
# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
 
{
    'name': 'Category Pricelist Percentaje',
    'summary': """Add pricelist to product categories percentaje""",
    'version': '12.0.1.0.0',
    'description': """Add pricelist to product categories percentaje""",
    'author': 'DDL, Manuel Calero',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.es',
    'category': 'Extra Tools',
    'depends': [
        'base',
        'product',
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

# Copyright © 2018 Garazd Creation (https://garazd.biz)
# @author: Yurii Razumovskyi (support@garazd.biz)
# @author: Iryna Razumovska (support@garazd.biz)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

{
    'name': 'Custom Product Labels',
    'version': '18.0.1.0.1',
    'category': 'Extra Tools',
    'author': 'Garazd Creation',
    'website': 'https://garazd.biz/en/shop/category/odoo-product-labels-15',
    'license': 'LGPL-3',
    'summary': 'Print custom product labels with barcode | Barcode Product Label',
    'images': ['static/description/banner.png', 'static/description/icon.png'],
    'live_test_url': 'https://garazd.biz/r/V3Y',
    'depends': [
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/print_label_type_data.xml',
        'data/ir_filters_data.xml',
        'report/product_label_reports.xml',
        'report/product_label_templates.xml',
        'wizard/print_product_label_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
        'demo/ir_filters_demo.xml',
    ],
    'support': 'support@garazd.biz',
    'application': True,
    'installable': True,
    'auto_install': False,
}

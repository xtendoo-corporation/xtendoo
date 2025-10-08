{
    'name': 'Xtendoo - Descuentos Globales de Cliente',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Gestión de descuentos globales por cliente en ventas',
    'description': '''
        Este módulo permite:
        - Configurar descuentos globales por cliente
        - Aplicar automáticamente descuentos en presupuestos, pedidos y facturas
        - Botón manual para aplicar descuentos en documentos de venta
        - Funcionalidad similar a los descuentos al pie de Odoo 18.0
    ''',
    'author': 'Manuel Calero - Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'account',
        'sale_management',
        'sale_global_discount',
        'account_global_discount',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'wizard/apply_partner_discounts_wizard_views.xml',
        'data/partner_discount_data.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

{
    'name': 'Descuentos en Tarifas de Precios',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Añade campo de descuento en tarifas de precios que se aplica automáticamente en ventas',
    'description': '''
        Este módulo extiende las tarifas de precios de Odoo añadiendo un campo de descuento en las líneas
        de tarifa. Cuando se selecciona un producto con descuento configurado en una línea de venta,
        el descuento se aplica automáticamente.
    ''',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'product',
        'sale_management',
    ],
    'data': [
        'views/product_pricelist_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

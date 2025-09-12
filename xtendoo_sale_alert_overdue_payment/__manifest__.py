{
    'name': 'Alerta de Venta - Pagos Vencidos',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Alerta a los usuarios sobre clientes con facturas vencidas en pedidos de venta',
    'description': """
        Este módulo proporciona alertas para clientes con facturas vencidas:
        - Muestra un banner rojo en la cabecera del pedido de venta para clientes con pagos vencidos
        - Permite ver las facturas vencidas directamente desde el pedido
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'sale',
        'account',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

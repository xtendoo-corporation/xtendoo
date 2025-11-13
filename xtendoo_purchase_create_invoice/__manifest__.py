{
    'name': 'Xtendoo Purchase Create Invoice',
    'version': '19.0.2.0.0',
    'category': 'Purchases',
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'summary': 'Permite crear facturas de compra directamente con un solo clic, sin subir documentos ni wizards',
    'description': """
        Xtendoo Purchase Create Invoice
        ================================

        Este módulo añade una funcionalidad alternativa al flujo de trabajo de compras en Odoo 19.0.

        En Odoo 19.0, el flujo estándar para crear una factura de compra requiere subir un documento.
        Este módulo proporciona una alternativa permitiendo crear la factura directamente desde el
        pedido a proveedor con un solo clic.

        Características:
        ---------------
        * Botón "Crear Factura" que crea la factura directamente (un solo clic)
        * Factura automáticamente las cantidades pendientes de facturar (recibidas pero no facturadas)
        * No requiere subir documentos
        * No requiere wizards ni intervención del usuario
        * Proceso instantáneo y automático
        * Mantiene la compatibilidad con el flujo estándar de subir documentos
    """,
    'depends': [
        'purchase',
        'account',
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
}


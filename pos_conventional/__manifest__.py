{
    'name': 'POS Conventional (No táctil)',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Modo de punto de venta optimizado para equipos sin pantalla táctil',
    'description': """
        Añade una opción en la configuración del Punto de Venta para activar
        un modo optimizado para equipos sin pantalla táctil.
    """,
    'author': 'Guillermo Bárcena López',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/pos_config_kanban_views.xml',
        'views/pos_session_opening_wizard_views.xml',
        'views/pos_session_closing_wizard_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_conventional/static/src/js/pos_order_list_controller.js',
            'pos_conventional/static/src/xml/pos_order_list_view.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}


{
    'name': 'Stock Minimum Notification',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Notificaciones de stock mínimo usando OdooBot',
    'author': 'Dani',
    'website': '',
    'depends': ['base', 'stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_notification_views.xml',
        'wizards/stock_notification_wizard_views.xml',
        'data/cron_data.xml',
    ],
    'installable': True,
    'application': False,
}

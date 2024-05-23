{
    'name': 'APK Firebase Notifications',
    'version': '16.0',
    'summary': 'Integrate Firebase Notifications in Odoo',
    'description': 'A module to integrate Firebase Cloud Messaging for notifications in Odoo',
    'author': "Abraham Carrasco Xtendoo, Salvador González Jiménez",
    'category': 'Extra Tools',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'views/firebase_notification_view.xml',
        'views/firebase_json_upload_view.xml',
        'views/res_config_view_notifications.xml',
        'data/cron.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

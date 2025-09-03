{
    'name': 'Xtendoo Calendar WhatsApp Reminder',
    'version': '18.0.1.0.0',
    'category': 'Calendar',
    'summary': 'Enviar recordatorios de eventos de calendario por WhatsApp',
    'description': """
        Este módulo permite enviar recordatorios de eventos de calendario por WhatsApp.

        Características:
        - Recordatorios automáticos por WhatsApp para eventos de calendario
        - Plantillas personalizables para mensajes
        - Configuración de tiempo de recordatorio
        - Logs de envío y seguimiento
        - Integración con WhatsApp Business API
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'LGPL-3',
    'depends': [
        'calendar',
        'whatsapp',
        'contacts'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/calendar_event_views.xml',
        'views/calendar_reminder_views.xml',
        'data/whatsapp_template_data.xml',
        'data/cron_jobs.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

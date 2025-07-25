{
    'name': 'Xtendoo WhatsApp Attendance',
    'version': '18.0.1.0.0',
    'category': 'WhatsApp',
    'summary': 'Módulo para heredar webhook de WhatsApp y mostrar información de asistencia',
    'description': """
        Este módulo hereda el controlador webhook de WhatsApp para mostrar
        toda la información recibida mediante prints y gestionar asistencia.
        Permite configurar palabras clave personalizables y plantillas de respuesta.
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'depends': ['base', 'whatsapp', 'hr', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/whatsapp_templates.xml',
        'views/attendance_keyword_config_views.xml',
        'data/default_keywords.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

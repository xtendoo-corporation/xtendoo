{
    'name': 'Xtendoo WhatsApp Attendance - Location Always',
    'version': '19.0.1.0.0',
    'category': 'WhatsApp',
    'summary': 'WhatsApp Attendance with mandatory location sharing',
    'description': """
        Este módulo hereda el controlador webhook de WhatsApp para gestionar asistencia
        con solicitud automática de ubicación.

        A diferencia del módulo base, este módulo SIEMPRE solicita la ubicación
        sin preguntar al usuario si desea compartirla.

        Características:
        - Registro automático de entrada/salida mediante comandos de WhatsApp
        - Solicitud automática de ubicación (sin pregunta previa)
        - Palabras clave personalizables
        - Plantillas de respuesta configurables
        - Geolocalización obligatoria para todos los empleados con el módulo activado
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'LGPL-3',
    'depends': ['base', 'whatsapp', 'hr', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/whatsapp_templates.xml',
        'views/attendance_keyword_config_views.xml',
        'views/hr_employee_geolocation_views.xml',
        'data/default_keywords.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

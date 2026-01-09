# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Xtendoo WhatsApp Attendance - Location Always Community',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendance',
    'summary': 'WhatsApp Attendance con solicitud automática de ubicación usando Gateway Community',
    'description': """
        Este módulo gestiona asistencia con solicitud automática de ubicación
        usando el Gateway Community (xtendoo_mail_gateway_whatsapp).

        A diferencia del módulo base (xtendoo_whatsapp_attendance_comunity),
        este módulo SIEMPRE solicita la ubicación sin preguntar al usuario
        si desea compartirla.

        Características:
        - Registro automático de entrada/salida mediante comandos de WhatsApp
        - Solicitud automática de ubicación (sin pregunta previa)
        - Palabras clave personalizables
        - Mensajes de respuesta configurables (confirmación, solicitud de ubicación, confirmación de ubicación)
        - Geolocalización obligatoria para todos los empleados
        - Campos separados para ubicación de entrada y salida
        - Visualización de ubicaciones en Google Maps

        Este módulo es INDEPENDIENTE y no requiere xtendoo_whatsapp_attendance_comunity.
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_attendance',
        'xtendoo_mail_gateway',
        'xtendoo_mail_gateway_whatsapp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/default_keywords.xml',
        'views/attendance_keyword_config_views.xml',
        'views/hr_employee_geolocation_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Xtendoo WhatsApp Attendance - Location Always Community',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendance',
    'summary': 'WhatsApp Attendance con solicitud automática de ubicación usando Gateway Community',
    'description': """
        Este módulo hereda de xtendoo_whatsapp_attendance_comunity para gestionar asistencia
        con solicitud automática de ubicación usando el Gateway Community.

        A diferencia del módulo base, este módulo SIEMPRE solicita la ubicación
        sin preguntar al usuario si desea compartirla.

        Características:
        - Registro automático de entrada/salida mediante comandos de WhatsApp
        - Solicitud automática de ubicación (sin pregunta previa)
        - Palabras clave personalizables
        - Mensajes de respuesta configurables
        - Geolocalización obligatoria para todos los empleados con el módulo activado
        - Campos separados para ubicación de entrada y salida
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'LGPL-3',
    'depends': [
        'xtendoo_whatsapp_attendance_comunity',
    ],
    'data': [
        'views/hr_employee_geolocation_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


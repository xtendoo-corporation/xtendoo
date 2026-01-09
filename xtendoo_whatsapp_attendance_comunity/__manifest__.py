# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Xtendoo WhatsApp Attendance Community',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Módulo para gestionar asistencia mediante WhatsApp usando el Gateway Community',
    'description': """
        Este módulo permite registrar la asistencia de empleados mediante mensajes de WhatsApp
        usando el módulo xtendoo_mail_gateway_whatsapp en lugar del WhatsApp Enterprise de Odoo.

        Características:
        - Registro automático de entrada/salida mediante comandos de WhatsApp
        - Palabras clave personalizables para entrada y salida
        - Plantillas de respuesta configurables
        - Geolocalización opcional para verificar ubicación de empleados
        - Integración con hr_attendance para registros oficiales
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
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


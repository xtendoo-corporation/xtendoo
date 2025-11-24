{
    'name': 'Xtendoo WhatsApp Vacation',
    'version': '18.0.1.0',
    'category': 'WhatsApp',
    'summary': 'Solicitar vacaciones a través de WhatsApp',
    'description': """
        Este módulo permite a los empleados solicitar vacaciones directamente desde WhatsApp.

        Características:
        - Solicitud de vacaciones por comandos de WhatsApp
        - Flujo conversacional guiado paso a paso
        - Validación de fechas y días disponibles
        - Creación automática de solicitudes en Odoo
        - Palabras clave personalizables
        - Cancelación en cualquier momento con /cancelar
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'AGPL-3',
    'depends': ['base', 'whatsapp', 'hr', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'data/whatsapp_templates.xml',
        'data/vacation_keywords.xml',
        'views/vacation_keyword_config_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

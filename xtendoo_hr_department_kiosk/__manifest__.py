# -*- coding: utf-8 -*-
{
    'name': 'Xtendoo HR Department Kiosk',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Filtro por departamento en el kiosco oficial de Odoo',
    'description': """
        Este módulo añade la posibilidad de filtrar el kiosco oficial de asistencia de Odoo por departamento
        mediante una URL específica. Utiliza el diseño y funcionalidad nativa de Odoo.
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'depends': [
        'hr',
        'hr_attendance',
    ],
    'data': [
        'views/hr_department_views.xml',
        'views/hr_attendance_kiosk_templates.xml',
    ],
    'assets': {
        'hr_attendance.assets_public_attendance': [
            'xtendoo_hr_department_kiosk/static/src/public_kiosk/public_kiosk_app_patch.js',
            'xtendoo_hr_department_kiosk/static/src/components/manual_selection/manual_selection_patch.js',
            'xtendoo_hr_department_kiosk/static/src/components/manual_selection/manual_selection_patch.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

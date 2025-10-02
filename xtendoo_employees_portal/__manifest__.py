{
    'name': 'Portal Empleados Multiusuario',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'hr_timesheet', 'portal', 'website'],
    'data': [
        'views/portal_templates.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
}

{
    'name': 'Portal Empleados Multiusuario',
    'version': '1.0',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'hr_timesheet', 'portal', 'website'],
    'data': [
        'views/portal_templates.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
}

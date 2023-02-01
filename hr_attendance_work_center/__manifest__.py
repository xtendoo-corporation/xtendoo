{
    "name": "Asistencias con centro de trabajo",
    "summary": """Asistencias con centro de trabajo""",
    "version": "15.1.0.0",
    "description": """Asistencias con centro de trabajo""",
    "author": "Daniel Dominguez",
    "company": "Xtendoo",
    "website": "http://xtendoo.es",
    "category": "Extra Tools",
    "license": "AGPL-3",
    "depends": [
        "contacts",
        "hr_attendance",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_work_center.xml",
        "views/res_partner_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            '/hr_attendance_work_center/static/src/js/work_center.js',
            '/hr_attendance_work_center/static/src/js/partner_kanban_view_handler.js',
            '/hr_attendance_work_center/static/src/js/work_center_confirm.js',
        ],
        'web.assets_qweb': [
            'hr_attendance_work_center/static/src/xml/**/*',
        ],
    },
    "installable": True,
    "auto_install": False,
}

{
    "name": "Asistencias con centro de trabajo",
    "summary": """Asistencias con centro de trabajo""",
    "version": "18.0.1.0.1",
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
        "views/hr_attendance_work_center.xml",
        "views/res_partner_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            '/hr_attendance_work_center/static/src/js/greeting_action.js',
            '/hr_attendance_work_center/static/src/js/work_center.js',
            '/hr_attendance_work_center/static/src/js/work_center_confirm.js',
            '/hr_attendance_work_center/static/src/xml/attendance_work_center.xml',
            '/hr_attendance_work_center/static/src/xml/greeting_action.xml',
        ],
    },
    "installable": True,
    "auto_install": False,
}

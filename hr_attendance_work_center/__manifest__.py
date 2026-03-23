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
        "security/ir.model.access.csv",
        "views/hr_attendance_work_center.xml",
        "views/res_partner_view.xml",
        "wizard/update_coste_wizard_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            '/hr_attendance_work_center/static/src/js/work_center.js',
            '/hr_attendance_work_center/static/src/xml/attendance_work_center.xml',
            '/hr_attendance_work_center/static/src/scss/attendance_work_center.scss',
        ],
        'hr_attendance.assets_public_attendance': [
            '/hr_attendance_work_center/static/src/js/public_kiosk_work_center.js',
            '/hr_attendance_work_center/static/src/xml/public_kiosk_work_center.xml',
        ],
    },
    "installable": True,
    "auto_install": False,
}

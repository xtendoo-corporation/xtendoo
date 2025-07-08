{
    "name": "Employee Portal",
    "summary": "Portal de empleados con autenticación por PIN",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "hr",
        "hr_attendance",
        "hr_holidays",
        "web",
        "resource",
    ],
    "data": [
        "security/employee_portal_security.xml",
        "security/ir.model.access.csv",
        "views/employee_portal_views.xml",
        "views/employee_portal_templates.xml",
        "views/hr_employee_views.xml",
        "views/employee_portal_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "xtendoo_employee_portal/static/src/js/employee_login.js",
            "xtendoo_employee_portal/static/src/css/employee_portal.css",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "optional_depends": ["hr_timesheet"],
}

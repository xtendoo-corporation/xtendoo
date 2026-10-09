{
    "name": "Xtendoo HR Attendance Mobile Portal",
    "summary": "Fichaje desde el móvil sin cuenta de Odoo (portal web + PWA básica)",
    "description": """
Portal web móvil para que los empleados fichen entrada/salida sobre el modelo
estándar hr.attendance, sin usuario de backend.

* Activación individual con enlace de un solo uso y caducidad.
* Sesión propia por dispositivo (cookie segura), revocable.
* Geolocalización del navegador solo al pulsar el botón (sin seguimiento).
* Historial personal paginado.
* Manifiesto web para guardar el acceso en la pantalla de inicio.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Attendances",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": ["hr_attendance"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/hr_attendance_views.xml",
        "views/portal_access_views.xml",
        "views/res_config_settings_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

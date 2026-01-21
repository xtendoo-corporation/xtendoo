{
    "name": "HR Attendance Phone",
    "version": "1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Registro de asistencia mediante teléfono y PIN en el modo quiosco",
    "description": """
        Módulo que extiende el sistema de asistencias de Odoo para permitir
        el registro de asistencia mediante número de teléfono y PIN desde
        el modo quiosco (kiosk mode).

        Características:
        - Botón adicional en el modo quiosco para acceso por teléfono
        - Pantalla para ingreso de teléfono y PIN
        - Validación contra empleados registrados
        - Optimizado para uso desde móviles
    """,
    "author": "Xtendoo",
    "depends": ["hr_attendance", "web"],
    "data": [
        "views/template.xml",
    ],
    "assets": {
        "hr_attendance.assets_public_attendance": [
            "xtendoo_hr_attendance_phone/static/src/js/attendance_phone.js",
            "xtendoo_hr_attendance_phone/static/src/xml/attendance_phone_modal.xml",
            "xtendoo_hr_attendance_phone/static/src/css/attendance_phone.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}

{
    "name": "APPCC Registration System",
    "version": "19.0.1.0.0",
    "summary": "Verificacion global anual del sistema APPCC",
    "category": "Quality",
    "author": "Xtendoo",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "report/appcc_registration_report.xml",
        "data/mail_template_data.xml",
        "views/appcc_registration_views.xml",
        "views/appcc_registration_menus.xml"
    ],
    "installable": True,
    "application": False,
}

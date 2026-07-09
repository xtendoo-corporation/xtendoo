{
    "name": "Xtendoo HR Leave Calendar Recompute",
    "summary": "Controla el calendario usado para recalcular duraciones de ausencias",
    "version": "19.0.1.0.0",
    "author": "Xtendoo",
    "license": "LGPL-3",
    "depends": [
        "hr_holidays",
        "resource",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_leave_recompute_wizard_views.xml",
        "views/hr_leave_views.xml",
        "data/server_actions.xml",
    ],
    "installable": True,
    "application": False,
}

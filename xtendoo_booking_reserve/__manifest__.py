{
    "name": "Xtendoo Booking Reserve",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Reserva sencilla desde website",
    "description": "Página web para recoger datos básicos y seleccionar fecha",
    "author": "Xtendoo",
    "license": "LGPL-3",
    "depends": ["website", "resource_booking"],
    "data": [
        "security/ir.model.access.csv",
        "views/booking_request_views.xml",
        "views/website_menu.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "web/static/lib/fullcalendar/core/index.global.js",
            "web/static/lib/fullcalendar/daygrid/index.global.js",
            "web/static/lib/fullcalendar/timegrid/index.global.js",
            "web/static/lib/fullcalendar/interaction/index.global.js",
            "web/static/lib/fullcalendar/luxon3/index.global.js",
            "web/static/lib/fullcalendar/luxon3/index.global.js",
            "xtendoo_booking_reserve/static/src/js/booking.js",
            "xtendoo_booking_reserve/static/src/css/booking.css",
        ]
    },
    "installable": True,
    "application": False,
}

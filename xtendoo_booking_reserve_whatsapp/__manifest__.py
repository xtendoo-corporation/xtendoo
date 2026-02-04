{
    "name": "Xtendoo Booking Reserve - WhatsApp Integration",
    "version": "18.0.1.0.0",
    "category": "Social",
    "summary": "WhatsApp integration for Booking Reserve",
    "author": "Xtendoo",
    "license": "AGPL-3",
    "depends": [
        "xtendoo_booking_reserve",
        "mail_gateway_whatsapp_chatter",
        "mail_gateway_whatsapp_variables",
        "calendar",
    ],
    "data": [
        "data/whatsapp_template.xml",
        "views/templates.xml",
        "views/res_partner_views.xml",
        "views/calendar_alarm_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_frontend": [
            "xtendoo_booking_reserve_whatsapp/static/src/js/booking_whatsapp.js",
        ]
    },
    "installable": True,
    "auto_install": False,
}

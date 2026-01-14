# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo WhatsApp POS Ticket",
    "summary": "Enviar ticket de venta POS por WhatsApp al cliente",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
        "mail_gateway_whatsapp",
        "mail_gateway_whatsapp_variables",
        "xtendoo_pos_receipt"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/whatsapp_template_data.xml",
        "views/pos_config_views.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_whatsapp_pos_ticket/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

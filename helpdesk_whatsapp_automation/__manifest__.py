# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Helpdesk WhatsApp Automation",
    "version": "18.0.1.0.0",
    "category": "Helpdesk",
    "summary": "Automate helpdesk ticket creation via WhatsApp and manage communication",
    "author": "Xtendoo",
    "website": "https://github.com/xtendoo-corporation",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "helpdesk_type",
        "mail_gateway_whatsapp_chatter",
        "mail_gateway_whatsapp_variables",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_whatsapp_template_data.xml",
        "data/helpdesk_ticket_type_data.xml",
        "data/mail_template_assigned_employee.xml",
        "data/mail_template_closed_ticket.xml",
        "views/res_partner_views.xml",
        "views/discuss_channel_views.xml",
        "views/res_config_settings_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_dashboard_views.xml",
    ],
    "installable": True,
    "application": False,
}

# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_default_manager_id = fields.Many2one(
        "res.users",
        string="Manager de comunicación por defecto",
        help="Usuario que se asignará por defecto a los contactos si no tienen uno específico.",
    )
    incident_request_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla de solicitud de incidencia",
        help="Plantilla que se enviará al cliente cuando escriba /ticket.",
    )

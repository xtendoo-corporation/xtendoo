# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    communication_manager_id = fields.Many2one(
        "res.users",
        string="Encargado de comunicación",
        default=lambda self: self.env.company.whatsapp_default_manager_id,
        help="Empleado responsable de gestionar la comunicación con este cliente.",
    )
    communication_employee_id = fields.Many2one(
        "res.users",
        string="Empleado para comunicación",
        help="Empleado asignado para la comunicación directa con este cliente.",
    )

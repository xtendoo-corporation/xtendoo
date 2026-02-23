# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    assigned_employee_id = fields.Many2one(
        "res.users",
        string="Empleado Asignado",
        help="Empleado asignado para la comunicación de este ticket.",
    )

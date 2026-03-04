# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    communication_manager_id = fields.Many2one(
        "res.users",
        string="Encargado de comunicación",
        help="Empleado responsable de gestionar la comunicación con este cliente.",
    )
    communication_employee_id = fields.Many2one(
        "res.users",
        string="Empleado para comunicación",
        help="Empleado asignado para la comunicación directa con este cliente.",
    )

    @api.model
    def default_get(self, fields_list):
        """Set default communication_manager_id from company settings.

        We use default_get instead of a field default=lambda because during
        module installation the res_company column may not exist yet, which
        would cause a psycopg2.errors.UndefinedColumn crash.
        """
        res = super().default_get(fields_list)
        if "communication_manager_id" in fields_list and not res.get(
            "communication_manager_id"
        ):
            try:
                manager = self.env.company.whatsapp_default_manager_id
                if manager:
                    res["communication_manager_id"] = manager.id
            except Exception:
                _logger.debug(
                    "Could not read whatsapp_default_manager_id from company "
                    "(may not be installed yet)."
                )
        return res


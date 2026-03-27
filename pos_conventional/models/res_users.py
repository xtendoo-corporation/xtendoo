# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    pin = fields.Char(
        string="PIN del usuario",
        help="PIN utilizado para el punto de venta convencional.",
    )

    _sql_constraints = [
        ("pin_unique", "unique(pin)", "El PIN del usuario debe ser único."),
    ]

    @api.constrains("pin")
    def _check_pin_unique(self):
        for record in self:
            if record.pin:
                duplicate = self.search(
                    [("pin", "=", record.pin), ("id", "!=", record.id)], limit=1
                )
                if duplicate:
                    raise ValidationError(
                        _(
                            "El PIN '%s' ya está en uso por el usuario '%s'. "
                            "Por favor, elija un PIN diferente."
                        )
                        % (record.pin, duplicate.name)
                    )

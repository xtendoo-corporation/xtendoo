# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    pin = fields.Char(
        string="PIN del usuario",
        help="PIN utilizado para el punto de venta convencional.",
    )

    allowed_pos_config_ids = fields.Many2many(
        'pos.config',
        'res_users_pos_config_rel',
        'user_id',
        'pos_config_id',
        string='Cajas permitidas (POS)',
        help='Cajas (puntos de venta) a las que el usuario puede acceder. Filtrado por las compañías asignadas al usuario.',
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

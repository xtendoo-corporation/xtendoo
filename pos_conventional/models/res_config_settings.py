# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_non_touch = fields.Boolean(
        related="pos_config_id.pos_non_touch",
        readonly=False,
        string="POS no táctil",
        help="Activa un modo de venta optimizado para equipos sin pantalla táctil.",
    )

    pos_default_partner_id = fields.Many2one(
        "res.partner",
        related="pos_config_id.default_partner_id",
        readonly=False,
        string="Cliente por Defecto",
        help="Cliente que se asignará automáticamente a los nuevos pedidos creados desde el backend.",
        domain="[('customer_rank', '>', 0)]",
    )

    pos_enable_albaran = fields.Boolean(
        related="pos_config_id.pos_enable_albaran",
        readonly=False,
        string="Albarán desde el POS",
        help="Permite crear albaranes desde el POS.",
    )

    pos_force_employee_login_after_order = fields.Boolean(
        related="pos_config_id.pos_force_employee_login_after_order",
        readonly=False,
        string="Pedir PIN tras venta",
        help="Si está activo, pedirá el PIN del empleado después de cada venta y cambiará el usuario de la sesión.",
    )

    has_open_pos_sessions = fields.Boolean(
        string="Tiene sesiones POS abiertas",
        compute="_compute_has_open_pos_sessions",
        readonly=True,
        help="Indica si existe alguna sesión POS abierta en la base de datos.",
    )

    @api.depends("pos_config_id.session_ids.state")
    def _compute_has_open_pos_sessions(self):
        for settings in self:

            if not settings.pos_config_id:
                settings.has_open_pos_sessions = False
                continue

            open_sessions_count = self.env["pos.session"].search_count(
                [
                    ("config_id", "=", settings.pos_config_id.id),
                    ("state", "!=", "closed"),
                ]
            )
            settings.has_open_pos_sessions = open_sessions_count > 0

    def set_values(self):

        for record in self:
            # Si pos_config_id no está establecido, saltamos la validación
            if not record.pos_config_id:
                continue

            # Recalculamos manualmente si tiene sesiones abiertas para asegurar el dato
            has_open = (
                self.env["pos.session"].search_count(
                    [
                        ("config_id", "=", record.pos_config_id.id),
                        ("state", "!=", "closed"),
                    ]
                )
                > 0
            )

            if has_open:
                # valor actual en la base de datos real (pos.config)
                current = bool(record.pos_config_id.pos_non_touch)
                # nuevo valor que intenta guardar el usuario
                new = bool(record.pos_non_touch)

                if current != new:
                    raise UserError(
                        "No se puede cambiar el modo táctil/no táctil mientras existan sesiones POS abiertas.\n"
                        "Por favor, cierre las sesiones abiertas antes de modificar esta opción."
                    )
        return super(ResConfigSettings, self).set_values()

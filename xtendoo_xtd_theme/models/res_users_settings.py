# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    color_scheme = fields.Selection(
        selection=[
            ("system", "System"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        default="system",
        required=True,
        string="Theme",
    )

    xtd_sidebar_app_order = fields.Json(
        default=list,
        string="Xtd Sidebar App Order",
    )
    xtd_sidebar_hidden_apps = fields.Json(
        default=list,
        string="Xtd Sidebar Hidden Apps",
    )
    # False = menú lateral contraído del todo (solo la flecha para sacarlo).
    xtd_show_sidebar = fields.Boolean(
        string="Show Xtd Sidebar Menu",
        default=True,
    )
    xtd_use_custom_dashboard = fields.Boolean(
        string="Use Custom Xtd Dashboard",
    )

    # Franja horaria visible en las vistas de día y semana del calendario.
    xtd_calendar_hour_start = fields.Integer(
        string="Calendar first visible hour",
        default=0,
    )
    xtd_calendar_hour_end = fields.Integer(
        string="Calendar last visible hour",
        default=24,
    )

    @api.constrains("xtd_calendar_hour_start", "xtd_calendar_hour_end")
    def _check_xtd_calendar_hours(self):
        for settings in self:
            start, end = settings.xtd_calendar_hour_start, settings.xtd_calendar_hour_end
            if not (0 <= start < end <= 24):
                raise ValidationError(self.env._(
                    "The visible calendar hours must satisfy 0 <= first hour < last hour <= 24."
                ))

# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    color_scheme = fields.Selection(
        related="res_users_settings_id.color_scheme",
        readonly=False,
    )
    xtd_use_custom_dashboard = fields.Boolean(
        related="res_users_settings_id.xtd_use_custom_dashboard",
        readonly=False,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "color_scheme",
            "xtd_use_custom_dashboard",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "color_scheme",
            "xtd_use_custom_dashboard",
        ]

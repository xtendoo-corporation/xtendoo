# -*- coding: utf-8 -*-

from odoo import fields, models


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


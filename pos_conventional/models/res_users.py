# -*- coding: utf-8 -*-
from odoo import fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    pin = fields.Char(
        string="PIN del usuario",
        help="PIN utilizado para el punto de venta convencional.",
    )

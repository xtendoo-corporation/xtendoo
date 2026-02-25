# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    see_all_companies = fields.Boolean(
        string="See All Companies",
        default=False,
        help="If checked, this user will bypass the strict company encapsulation rules.",
    )

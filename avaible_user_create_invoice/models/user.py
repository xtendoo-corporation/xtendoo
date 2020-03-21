# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Users(models.Model):
    _inherit = "res.users"

    create_direct_invoice = fields.Boolean(
        string='create_direct_invoice',
        default="False"
        )

# -*- coding: utf-8 -*-
from odoo import models, fields


class PosCategory(models.Model):
    _inherit = 'pos.category'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        index=True,
    )


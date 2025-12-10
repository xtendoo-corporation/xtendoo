# -*- coding: utf-8 -*-
from odoo import models, fields


class PosNote(models.Model):
    _inherit = 'pos.note'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        index=True,
    )


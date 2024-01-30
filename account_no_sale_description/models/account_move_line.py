# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    @api.depends('product_id')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if line.product_id:
                lang = line.move_id.partner_id.lang
                line.name = line.product_id.with_context(lang=lang).name or ''

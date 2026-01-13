from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id_apply_global_discount(self):
        for line in self:
            partner = line.move_id.partner_id
            if partner and line.product_id and not line.product_id.no_global_discount:
                line.discount = partner.global_discount or 0.0
            elif line.product_id and line.product_id.no_global_discount:
                line.discount = 0.0

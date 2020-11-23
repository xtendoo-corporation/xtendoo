from odoo import models, fields


class SalePromotionQty(models.Model):
    _name = 'sale.promotion.qty'
    _order = 'promotion_id,start'

    start = fields.Float(
        string='Start')
    value = fields.Float(
        string='Value')
    promotion_id = fields.Many2one(
        comodel_name='sale.promotion',
        string='Promotion')

from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="POS Order",
    )

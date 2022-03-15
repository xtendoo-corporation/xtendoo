from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_line_discount_ids = fields.Many2many(string="Inline Discounts", comodel_name='sale.inline.discount',

                                              )


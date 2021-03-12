from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_city = fields.Char(string='Cuidad',
                        related='partner_id.city')

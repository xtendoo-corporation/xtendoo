from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_value = fields.Date(
        string='Value Date',
        default=fields.Date.context_today,
        index=True
    )


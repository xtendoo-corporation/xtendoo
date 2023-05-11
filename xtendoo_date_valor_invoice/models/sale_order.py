from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_valor = fields.Datetime(string='Fecha Valor', index=True)

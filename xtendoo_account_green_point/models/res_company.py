from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    green_point_affects_cost = fields.Boolean(string="Punto Verde Afecta Coste", default=False)
    green_point_enabled_accounting_split = fields.Boolean(string="Desglose Contable Punto Verde", default=False)
    green_point_purchase_account_id = fields.Many2one('account.account', string="Cuenta de Compras Punto Verde")

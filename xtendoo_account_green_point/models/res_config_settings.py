from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    green_point_affects_cost = fields.Boolean(related='company_id.green_point_affects_cost', readonly=False)
    green_point_enabled_accounting_split = fields.Boolean(related='company_id.green_point_enabled_accounting_split', readonly=False)
    green_point_purchase_account_id = fields.Many2one(related='company_id.green_point_purchase_account_id', readonly=False)

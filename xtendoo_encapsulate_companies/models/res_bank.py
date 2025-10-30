from odoo import models, fields

class ResBank(models.Model):
    _inherit = 'res.bank'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)

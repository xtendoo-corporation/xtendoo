from odoo import models, fields

class ResPartnerIndustry(models.Model):
    _inherit = 'res.partner.industry'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


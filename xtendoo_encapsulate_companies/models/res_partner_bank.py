from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, index=True, readonly=False)

    def create(self, vals_list):
        # Si es una lista de diccionarios
        if isinstance(vals_list, list):
            for vals in vals_list:
                if 'company_id' not in vals or not vals['company_id']:
                    vals['company_id'] = self.env.company.id
        # Si es un solo diccionario
        elif isinstance(vals_list, dict):
            if 'company_id' not in vals_list or not vals_list['company_id']:
                vals_list['company_id'] = self.env.company.id
        return super().create(vals_list)

    def write(self, vals):
        # Si company_id se pone a False/None, lo restauramos al valor anterior
        if 'company_id' in vals and not vals['company_id']:
            for record in self:
                vals['company_id'] = record.company_id.id
        return super().write(vals)

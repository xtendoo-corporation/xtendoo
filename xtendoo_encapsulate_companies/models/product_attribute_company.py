from odoo import models, fields

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


class ProductTemplateAttributeExclusion(models.Model):
    _inherit = 'product.template.attribute.exclusion'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)



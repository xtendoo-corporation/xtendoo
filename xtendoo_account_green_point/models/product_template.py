from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    green_point_enabled = fields.Boolean(string="Punto Verde Activo", default=False)
    green_point_type = fields.Selection([
        ('unit', 'Por Unidad'),
        ('line', 'Fijo por Línea'),
        ('manual', 'Manual')
    ], string="Tipo Punto Verde", default='unit')
    
    green_point_amount = fields.Float(string="Importe Punto Verde", digits='Product Price')
    green_point_notes = fields.Char(string="Notas Punto Verde")

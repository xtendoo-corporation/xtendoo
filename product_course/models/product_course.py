# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductCourse(models.Model):
    _inherit = 'product.template'
    is_course = fields.Boolean('¿Es un curso?')
    course_type_name = fields.Char(string='Tipo de Curso')
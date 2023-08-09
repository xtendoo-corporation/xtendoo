# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ColorSample(models.Model):
    _name = "color.sample"
    _order = "sequence"

    sequence = fields.Integer()
    name = fields.Char(string='Value Name', required=True)
    image_large = fields.Image()
    view_mode = fields.Selection(
        [('hex_code', 'Hex Code'), ('image', 'Image')],
        required=True,
        default='hex_code'
    )
    hex_color = fields.Char()
    image_small = fields.Image()
    product_tmpl_id = fields.Many2one("product.template")

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Value name must be unique!'),
    ]

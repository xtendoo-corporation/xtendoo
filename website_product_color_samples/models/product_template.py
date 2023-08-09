# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    '''
    color_sample_ids = fields.One2many(
        'color.sample',
        'product_tmpl_id',
        string='Color Samples'
    )
'''
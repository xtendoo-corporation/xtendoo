# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    view_mode = fields.Selection([('hex_code', 'Hex Code'), ('image', 'Image')], required=True, default='hex_code')
    image_small = fields.Image()


"""
    view_mode = fields.Selection(
        related='product_tmpl_id.color_sample_ids.view_mode',
        store=True
    )
"""
"""
    image_small = fields.Image(
        related='product_tmpl_id.color_sample_ids.image_small',
        store=True
    )
"""

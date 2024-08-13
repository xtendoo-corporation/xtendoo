# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class WooProductAttributeTermEpt(models.Model):
    _name = "woo.product.attribute.term.ept"
    _description = "Product Attribute Term"

    name = fields.Char(required=1, translate=True)
    description = fields.Char()
    slug = fields.Char(help="An alphanumeric identifier for the resource unique to its type.")
    count = fields.Integer()
    woo_attribute_term_id = fields.Char()
    woo_attribute_id = fields.Char()
    exported_in_woo = fields.Boolean(default=False)
    attribute_id = fields.Many2one('product.attribute', 'Attribute', required=1, copy=False)
    attribute_value_id = fields.Many2one('product.attribute.value', 'Attribute Value', required=1, copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1, ondelete='cascade')

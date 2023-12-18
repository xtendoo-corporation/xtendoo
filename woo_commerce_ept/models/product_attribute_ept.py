# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class WooProductAttributeEpt(models.Model):
    _name = "woo.product.attribute.ept"
    _description = "Product Attribute"

    name = fields.Char(required=1, translate=True)
    slug = fields.Char(help="An alphanumeric identifier for the resource unique to its type.")
    order_by = fields.Selection([('menu_order', 'Custom Ordering'), ('name', 'Name'), ('name_num', 'Name(numeric)'),
                                 ('id', 'Term ID')], default="menu_order", string='Default Sort Order')
    woo_attribute_id = fields.Char()
    exported_in_woo = fields.Boolean(default=False)
    attribute_id = fields.Many2one('product.attribute', 'Attribute', required=1, copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1)
    attribute_type = fields.Selection([('select', 'Select'), ('text', 'Text')], default='select')
    has_archives = fields.Boolean(string="Enable Archives?", help="Enable/Disable attribute archives")

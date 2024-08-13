# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class StockPicking(models.Model):
    """
    Inherited to connect the picking with WooCommerce.
    @author: Maulik Barad on Date 14-Nov-2019.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """
    _inherit = "stock.picking"

    updated_in_woo = fields.Boolean(default=False)
    is_woo_delivery_order = fields.Boolean("WooCommerce Delivery Order")
    woo_instance_id = fields.Many2one("woo.instance.ept", "Woo Instance")
    canceled_in_woo = fields.Boolean("Cancelled In woo", default=False)

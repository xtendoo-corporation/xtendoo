# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_cod_available = fields.Boolean('Allow Cash on Delivery For Sale order', default=False)

# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ImportOrderStatusEpt(models.Model):
    """
    Model for managing status of sale orders while importing from Woo commerce.
    @author: Maulik Barad on Date 02-Nov-2019.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """
    _name = "import.order.status.ept"
    _description = "WooCommerce Order Status"

    name = fields.Char()
    status = fields.Char()

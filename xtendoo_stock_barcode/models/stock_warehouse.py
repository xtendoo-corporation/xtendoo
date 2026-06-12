# -*- coding: utf-8 -*-

from odoo import fields, models

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    tp_is_central_request_hub = fields.Boolean(
        string="Es Almacén Central (Hub)",
        default=False,
    )


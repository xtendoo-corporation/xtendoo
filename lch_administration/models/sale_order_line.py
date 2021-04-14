# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoice(models.Model):
    _inherit = ["sale.order.line", "administrator.mixin.rule"]
    _name = 'sale.order.line'

   

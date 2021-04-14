# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class SaleOrder(models.Model):
    _inherit = ['sale.order','administrator.mixin.rule']
    _name = 'sale.order'


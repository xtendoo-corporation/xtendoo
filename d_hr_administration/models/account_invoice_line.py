# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class AccountInvoiceLine(models.Model):
    _inherit = ['account.invoice.line','administrator.mixin.rule']
    _name = 'account.invoice.line'

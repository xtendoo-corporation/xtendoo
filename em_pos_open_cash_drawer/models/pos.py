# -*- coding: utf-8 -*-

from odoo import fields, models,tools,api
import logging

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_open_cash_d = fields.Boolean(related='pos_config_id.allow_open_cash_d', readonly=False)

class pos_config(models.Model):
    _inherit = 'pos.config' 

    allow_open_cash_d = fields.Boolean('Open Cash Drawer',default=True)


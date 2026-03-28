# -*- coding: utf-8 -*-

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_drawer_pos_enabled = fields.Boolean(
        related='pos_config_id.cash_drawer_pos_enabled',
        readonly=False,
    )
    cash_drawer_printer_select = fields.Char(
        related='pos_config_id.cash_drawer_printer_select',
        readonly=False,
    )
    cash_drawer_dummy_print = fields.Boolean(
        related='pos_config_id.cash_drawer_dummy_print',
        readonly=False,
    )
    cash_drawer_dummy_text = fields.Char(
        related='pos_config_id.cash_drawer_dummy_text',
        readonly=False,
    )
    cash_drawer_web_print_fallback = fields.Boolean(
        related='pos_config_id.cash_drawer_web_print_fallback',
        readonly=False,
    )

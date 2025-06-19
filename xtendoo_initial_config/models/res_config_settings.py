# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ovh_endpoint = fields.Char(string='Endpoint OVH', default='ovh-eu',
                              config_parameter='xtendoo_initial_config.ovh_endpoint',
                              help='Por ejemplo: ovh-eu para Europa o ovh-ca para Canadá')
    ovh_consumer_key = fields.Char(string='Consumer Key',
                                 config_parameter='xtendoo_initial_config.ovh_consumer_key')
    ovh_domain = fields.Char(string='Dominio de correo',
                           config_parameter='xtendoo_initial_config.ovh_domain',
                           help='El dominio para crear cuentas de correo, ej: example.com')

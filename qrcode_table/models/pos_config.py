# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    website_confirm_order_meesage = fields.Html(string='Website Confirm Order Message', translate=True,
                                                default=lambda s: _('We are preparing your order, Please patience we will serve you as soon as possible.'))

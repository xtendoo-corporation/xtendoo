# -- coding: utf-8 --


from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _name = 'sale.order'

    is_admin = fields.Boolean(
        comodel_name='sale.order',
        compute='_is_admin',
        string="isAdmin",
        default=lambda self: self._get_default_admin()
    )
    @api.one
    def _is_admin(self):
        self.is_admin=self.env.user.administration
        return

    @api.model
    def _get_default_admin(self):
        return self.env.user.administration

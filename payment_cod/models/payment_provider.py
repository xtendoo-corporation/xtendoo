# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.payment_cod import const
from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(
        string="Cash On Delivery",
        selection=[('cash_on_delivery', "Cash On Delivery")],
        required_if_provider='custom',
    )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.custom_mode != 'cash_on_delivery':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #


# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError


class account_payment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"

    def _get_partner_delivery_zone(self):
        if 'partner_delivery_zone_id' in request.session:
            return request.session['partner_delivery_zone_id']
        return 0

    delivery_zone_id = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string="Delivery Zone",
        ondelete='restrict',
        index=True,
        default=_get_partner_delivery_zone,
    )

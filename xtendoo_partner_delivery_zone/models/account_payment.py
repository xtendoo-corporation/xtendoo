# Copyright 2022 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.http import request


class account_payment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"

    def _get_partner_delivery_zone(self):
        if not request:
            return 0
        if 'partner_delivery_zone_id'not in request.session:
            return 0
        return request.session['partner_delivery_zone_id']

    delivery_zone_id = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string="Delivery Zone",
        ondelete='restrict',
        required=True,
        index=True,
        default=_get_partner_delivery_zone,
    )

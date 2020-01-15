# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, api

import logging


class PartnerDeliveryZone(models.Model):
    _name = 'partner.delivery.zone'
    _description = 'Partner delivery zone'

    name = fields.Char(
        string='Zone',
        required=True,
    )
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Partners',
    )
    visit_ids = fields.One2many(
        'partner.delivery.zone.visit',
        'delivery_zone_id',
        string='Delivery Zone Visit',
        auto_join=True,
    )

    @api.multi
    def set_values(self):
        super(PartnerDeliveryZone, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("partner.delivery.zone", self.code or '')

    def get_partners(self, delivery_zone_id):
        for partner in self.partner_ids:
            logging.info("#"*80)
            logging.info(partner)
            logging.info(partner.name)
        # return self.partner_ids.search(
        #     [('partner_delivery_zone_id', '=', delivery_zone_id)], order='sequence desc', limit=1)

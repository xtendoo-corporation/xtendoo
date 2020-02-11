# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

import logging


class PartnerDeliveryZoneWizard(models.TransientModel):
    _name = "partner.delivery.zone.wizard"
    _description = "Partner Delivery Zone Wizard"

    def _get_partner_delivery_zone(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('selected.partner.delivery.zone', 0))

    partner_delivery_zone = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string='Partner Delivery Zone',
        default=_get_partner_delivery_zone,
    )

    @api.multi
    def button_set_partner_delivery_zone(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(
            'selected.partner.delivery.zone', self.partner_delivery_zone.id)

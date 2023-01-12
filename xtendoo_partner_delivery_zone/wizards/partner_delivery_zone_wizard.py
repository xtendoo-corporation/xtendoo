# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.http import Controller, request, route
from odoo import api, fields, models, _

import logging


class PartnerDeliveryZoneWizard(models.TransientModel):
    _name = "partner.delivery.zone.wizard"
    _description = "Partner Delivery Zone Wizard"

    def _get_partner_delivery_zone(self):
        if 'partner_delivery_zone_id' in request.session:
            logging.info("***get request.session***")
            logging.info(request.session)
            return request.session['partner_delivery_zone_id']
        return 0

    partner_delivery_zone = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string='Partner Delivery Zone',
        default=_get_partner_delivery_zone,
    )

    def button_set_partner_delivery_zone(self):
        self.ensure_one()
        request.session['partner_delivery_zone_id'] = self.partner_delivery_zone.id
        logging.info("***set request.session***")
        logging.info(request.session)


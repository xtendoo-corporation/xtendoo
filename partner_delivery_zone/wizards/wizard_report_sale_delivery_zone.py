# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError

import logging


class WizardReportSaleDeliveryZone(models.TransientModel):
    _name = "wizard.report.sale.delivery.zone"
    _description = "Report Sale Delivery Zone Wizard"

    user_id = fields.Many2one(
        'res.users',
        string='User',
    )
    partner_delivery_zone = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string='Partner Delivery Zone',
    )
    date_report = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )

    def action_print_report(self):
        data = {
            'model': 'wizard.report.sale.delivery.zone',
            'form': self.read()[0],
            'active_ids': self._context['active_ids'],
        }
        return self.env.ref('partner_delivery_zone.report_sale').report_action(self, data=data)

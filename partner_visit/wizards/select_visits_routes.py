# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from datetime import datetime
from odoo.addons import decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class PartnerVisitDay(models.TransientModel):
    _name = 'partner.visit.day'
    _description = 'Partner Visit Day'

    user_id = fields.Many2one('res.users', 'Selection User')
    next_date = fields.Date(string='Next Visit')

    def _get_domain(self):
        domain = []
        if self.user_id.id:
            domain.append(('partner_id.user_id', '=', self.user_id.id))
        if self.next_date:
            domain.append(('next_date', '=', self.next_date))
        return domain

    def run_wizard(self):
        self.ensure_one()
        tree_view_id = self.env.ref('partner_visit.view_partner_visit_tree').id
        return {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree')],
            'view_mode': 'tree',
            'name': _('Partner Visit Day'),
            'res_model': 'partner.visit',
            'domain': self._get_domain()
        }
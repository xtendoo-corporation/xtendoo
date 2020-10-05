# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from datetime import date, datetime, time, timedelta

import logging

_logger = logging.getLogger(__name__)


class ReportPartnerVisit(models.TransientModel):
    _name = 'report.partner.visit'
    _description = 'Report Partner Visit'

    user_id = fields.Many2one('res.users', 'Selection User')
    date_begin = fields.Date(string='Begin')
    date_end = fields.Date(string='End')

    @api.onchange('user_id')
    def onchange_user_id(self):
        self.user_id = self.env.user.id
        self.date_begin = date.today() - timedelta(weeks=1)
        self.date_end = date.today()

    def _get_domain(self):
        domain = []
        if self.user_id.id:
            domain.append(('partner_id.user_id', '=', self.user_id.id))
        if self.date_begin:
            domain.append(('date', '>=', self.date_begin))
        if self.date_end:
            domain.append(('date', '<=', self.date_end))
        return domain

    def run_wizard(self):
        self.ensure_one()
        tree_view_id = self.env.ref('partner_visit.view_report_partner_visit_tree').id
        return {
            'name': _('Partner Route Visited'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(tree_view_id, 'tree')],
            'res_model': 'partner.visit.line',
            'domain': self._get_domain()
        }

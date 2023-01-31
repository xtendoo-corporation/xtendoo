from collections import OrderedDict

from odoo import api, models, _, fields
import json

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )

    workcenter_id_domain = fields.Char(
        compute="_compute_workcenter_id_domain",
        readonly=True,
        store=False,
    )

    def _compute_workcenter_id_domain(self):
        for rec in self:
            print("*"*120)
            print("Entra")
            print("*"*120)
            rec.workcenter_id_domain = json.dumps(
                [('is_work_center', '=', True)]
            )





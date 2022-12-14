from collections import OrderedDict

from odoo import api, models, _, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )

    # def work_center_manual(self, next_action, entered_pin=None):
    #     self.ensure_one()
    #     print("*"*80)
    #     print("Entra")
    #     print("*"*80)
    #     return {'warning': _('Wrong PIN')}

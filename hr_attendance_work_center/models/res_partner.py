from odoo import api, models, _, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )

from odoo import api, models, _, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )
    work_center_user_ids = fields.Many2many(
        comodel_name="work.center.partner.user",
        string="Work Center Partner User",
    )


class WorkcenterPartnerUser(models.Model):
    _name = 'work.center.partner.user'
    _description = 'Work Center Partner User'

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        domain=[("is_work_center", "=", True)],
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
    )


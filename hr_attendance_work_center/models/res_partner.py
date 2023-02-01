from odoo import api, models, _, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )
    # work_center_user_ids = fields.Many2many(
    #     comodel_name="work.center.partner.user",
    #     relation="work_center_partner_user",
    #     column1="partner_id",
    #     column2="user_id",
    #     string="Work Center Partner User",
    # )

    def _get_default_work_center_user_ids(self):
        return [(6, 0, [self.env.uid])]

    work_center_user_ids = fields.Many2many(
        'res.users',
        'work_center_partner_user',
        'partner_id',
        'user_id',
        default=_get_default_work_center_user_ids)


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


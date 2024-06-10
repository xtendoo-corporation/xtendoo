from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    access_notification = fields.Boolean(
        string="Permission to access notifications Push",
        help="If checked, the user will be able to access notifications push",
    )

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if vals.get('access_notification'):
            group = self.env.ref('firebase_notifications.group_apk_notifications')
            user.groups_id = [(4, group.id)]
        return user

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        if 'access_notification' in vals:
            group = self.env.ref('firebase_notifications.group_apk_notifications')
            for user in self:
                if vals['access_notification']:
                    user.groups_id = [(4, group.id)]
                else:
                    user.groups_id = [(3, group.id)]
        return res


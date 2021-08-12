# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    is_geolocated = fields.Boolean("Geolocated", default=False)

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        return res

    def write(self, vals):
        return super(ResUsers, self).write(vals)

    @api.model
    def change_geolocation(self, latitude, longitude):
        print("*"*80)
        print("*** latitude ***", latitude)
        print("*** longitude ***", longitude)

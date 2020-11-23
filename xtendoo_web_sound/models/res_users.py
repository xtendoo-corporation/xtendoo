# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    # counter_widget = fields.Integer('Counter Widget', default=1)

    @api.multi
    def play_sound_bell(self):
        print("sound_bell")
        return self.env.ref('xtendoo_web_sound.quiz_action').read()[0]
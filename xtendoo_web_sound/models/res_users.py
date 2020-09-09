# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    def play_sound_bell(self):
        print("sound_bell")


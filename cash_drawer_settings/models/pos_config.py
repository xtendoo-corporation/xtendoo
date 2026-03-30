# -*- coding: utf-8 -*-
from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    # [REMOVED] Configuration fields are no longer needed as per user request.
    # The 'Open Cash Drawer' functionality is now always active when the button is pressed.

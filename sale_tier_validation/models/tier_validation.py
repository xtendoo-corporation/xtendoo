# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ast import literal_eval


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    @api.model
    def _get_under_validation_exceptions(self):
        """Extend for more field exceptions."""
        return ['message_follower_ids', 'access_token']


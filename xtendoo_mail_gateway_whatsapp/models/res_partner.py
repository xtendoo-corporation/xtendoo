# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _whatsapp_get_partner(self):
        return self

    def _phone_get_number_fields(self):
        """This method returns the fields to use to find the number to use to
        send an SMS on a record."""
        if hasattr(super(), '_phone_get_number_fields'):
            result = set(super()._phone_get_number_fields())
        else:
            result = set()
        # Only add fields that actually exist in the model
        for fname in ("mobile", "phone"):
            if fname in self._fields:
                result.add(fname)
        return list(result)

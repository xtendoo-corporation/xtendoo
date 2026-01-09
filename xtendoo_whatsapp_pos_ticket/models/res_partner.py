# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _has_whatsapp_phone(self):
        """Verificar si el partner tiene teléfono para WhatsApp"""
        return bool(self.mobile or self.phone)


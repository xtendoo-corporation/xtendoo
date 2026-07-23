from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Extender el campo attendance_kiosk_mode para agregar las opciones de teléfono
    attendance_kiosk_mode = fields.Selection(
        selection_add=[("phone", "Teléfono + PIN"), ("phone_only", "Solo Teléfono")],
        ondelete={"phone": "set default", "phone_only": "set default"},
    )

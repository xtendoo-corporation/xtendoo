# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import re


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    # Campos para flujo de confirmación automática
    requires_confirmation = fields.Boolean(
        string="Requiere Confirmación",
        default=False,
        help="Si está marcado, esta plantilla espera una respuesta del cliente antes de enviar otra plantilla automáticamente"
    )
    confirmation_template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Plantilla tras Confirmación",
        help="Plantilla que se enviará automáticamente cuando el cliente responda"
    )
    confirmation_type = fields.Selection([
        ('button', 'Botón Interactivo (cualquier botón)'),
        ('text_si', 'Texto: "Sí" o "Si"'),
        ('text_ok', 'Texto: "OK" o "ok"'),
        ('any', 'Cualquier Respuesta')
    ], string="Tipo de Confirmación", default='button',
       help="Tipo de respuesta esperada para activar la plantilla de confirmación")

    @api.model
    def _prepare_values_to_import(self, gateway, json_data):
        vals = super()._prepare_values_to_import(gateway, json_data)
        # Si la plantilla está aprobada por Meta, la consideramos soportada
        if json_data.get("status", "").lower() == "approved":
            vals["is_supported"] = True
        return vals

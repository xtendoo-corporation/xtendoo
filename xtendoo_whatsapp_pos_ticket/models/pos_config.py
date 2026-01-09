# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    whatsapp_ticket_enabled = fields.Boolean(
        string="Habilitar envío de ticket por WhatsApp",
        default=False,
        help="Si está activado, se mostrará una opción para enviar el ticket por WhatsApp al cliente después de cada venta."
    )
    whatsapp_gateway_id = fields.Many2one(
        'mail.gateway',
        string="Gateway de WhatsApp",
        domain="[('gateway_type', '=', 'whatsapp')]",
        help="Gateway de WhatsApp a utilizar para enviar los tickets."
    )
    whatsapp_pos_template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Plantilla de WhatsApp",
        domain="[('gateway_id', '=', whatsapp_gateway_id)]",
        help="Plantilla de WhatsApp a utilizar para enviar los tickets."
    )


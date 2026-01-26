from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_opt_in = fields.Boolean(string="Recibir notificaciones por WhatsApp", default=False)

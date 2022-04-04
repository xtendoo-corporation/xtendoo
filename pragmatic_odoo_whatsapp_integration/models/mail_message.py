from odoo import fields, models, _


class mailMessage(models.Model):
    _inherit = 'mail.message'

    whatsapp_message_id = fields.Char('Whatsapp Message Id')

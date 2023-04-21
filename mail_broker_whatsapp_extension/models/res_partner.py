import logging
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    chatId = fields.Char('Chat ID')
    whatsapp_msg_ids = fields.One2many('whatsapp.messages', 'partner_id', 'WhatsApp Messages')

    mail_broker_channel_id = fields.One2many(
        "mail.broker.channel",
        "partner_id",
    )
    message_ids = fields.One2many(
        "mail.message.broker",
        related='mail_broker_channel_id.message_ids',
    )
    mail_message_ids = fields.One2many(
        "mail.message",
        related='mail_broker_channel_id.mail_message_ids',
    )


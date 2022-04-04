import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class WhatsappMessages(models.Model):
    _name = 'whatsapp.messages'
    _description = "Whatsapp Messages"

    name=fields.Char('Name', readonly=True)
    message_body = fields.Text('Message', readonly=True)
    message_id = fields.Text('Message Id', readonly=True)
    fromMe = fields.Boolean('Form Me', readonly=True)
    to = fields.Char('To', readonly=True)
    chatId = fields.Char('Chat ID', readonly=True)
    type = fields.Char('Type', readonly=True)
    msg_image = fields.Binary('Image', readonly=True)
    senderName = fields.Char('Sender Name', readonly=True)
    chatName = fields.Char('Chat Name', readonly=True)
    author = fields.Char('Author', readonly=True)
    time = fields.Datetime('Date and time', readonly=True)
    partner_id = fields.Many2one('res.partner','Partner', readonly=True)
    state= fields.Selection([('sent', 'Sent'),('received', 'Received')], readonly=True)
    attachment_id = fields.Many2one('ir.attachment', 'Attachment ', readonly=True)
    attachment_data = fields.Binary(related='attachment_id.datas', string='Attachment')
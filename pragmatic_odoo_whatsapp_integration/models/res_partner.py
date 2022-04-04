import logging
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    chatId = fields.Char('Chat ID')
    whatsapp_msg_ids = fields.One2many('whatsapp.messages', 'partner_id', 'WhatsApp Messages')

    def _get_default_whatsapp_recipients(self):
        """ Override of mail.thread method.
            WhatsApp recipients on partners are the partners themselves.
        """
        return self

from odoo import api, fields, models, _


class MailMessageState(models.Model):
    _inherit = 'mail.message'

    state = fields.Selection(
        [('sent', 'sent'),
         ('received', 'received'),
         ('exception', 'exception')],
        string='State',
        compute='_compute_message_state',
    )

    @api.depends('notification_ids')
    def _compute_message_state(self):
        for message in self:
            notifications = message.broker_notification_ids
            if not notifications:
                message.state = 'exception'
            elif all(notification.state == 'sent' for notification in notifications):
                message.state = 'sent'
            elif all(notification.state == 'received' for notification in notifications):
                message.state = 'received'
            else:
                message.state = 'exception'

from odoo import api, fields, models, _


class MailMessageState(models.Model):
    _inherit = 'mail.message'

    notification_status = fields.Selection(
        [('sent', 'Sent'),
         ('received', 'Received'),
         ('error', 'Error')],
        string='State',
        compute='_compute_message_state'
    )

    @api.depends('notification_ids.notification_status')
    def _compute_message_state(self):
        for message in self:
            notifications = message.notification_ids
            if all(notification.notification_status == "sent" for notification in notifications):
                message.state = "sent"
            elif all(notification.notification_status == "received" for notification in notifications):
                message.state = "received"
            else:
                message.state = message.customer_status or "error"

from odoo import api, fields, models, _


class MailMessageState(models.Model):
    _inherit = 'mail.message'

    state = fields.Selection(
        [('sent', 'Sent'),
         ('received', 'Received'),
         ('exception', 'Exception')],
        string='State',
        compute='_compute_message_state',
        default='exception',
    )

    @api.depends('notification_ids')
    def _compute_message_state(self):
        self.state = 'exception'
        for message in self:

            print("*"*80)
            print("message", message)
            print("*"*80)

            notifications = message.broker_notification_ids
            if not notifications:
                print("=" * 80)
                print("No hay notificaciones")
                print("=" * 80)

            for notification in notifications:
                print("=" * 80)
                print("notification_state", notification.state)
                print("=" * 80)

            if not notifications:
                message.state = 'exception'
            elif all(notification.state == 'sent' for notification in notifications):
                message.state = 'sent'
            elif all(notification.state == 'received' for notification in notifications):
                message.state = 'received'
            else:
                message.state = 'exception'


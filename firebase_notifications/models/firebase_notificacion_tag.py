from odoo import models, fields, api


class FirebaseNotificationTag(models.Model):
    _name = 'firebase.notification.tag'
    _description = 'Firebase Notification Tag'

    name = fields.Char('Name')
    color = fields.Integer('Color Index')

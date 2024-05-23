import os
import threading
import time

from odoo import models, fields, api
import firebase_admin
from firebase_admin import credentials, messaging, firestore
from datetime import datetime
import requests
import base64


class FirebaseNotification(models.Model):
    _name = 'firebase.notification'
    _description = 'Firebase Notification'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        'Name'
    )
    title = fields.Char(
        'Title'
    )
    body = fields.Text(
        'Body'
    )
    image = fields.Char(
        'Image URL'
    )
    image_preview = fields.Binary(
        "Image",
    )
    redirect_url = fields.Char(
        'Redirect URL'
    )
    tags = fields.Many2many(
        'firebase.notification.tag',
        string='Tags'
    )
    color = fields.Integer(
        'Color Index'
    )
    last_launch = fields.Datetime(
        'Last launch'
    )
    notification_sent = fields.Boolean(
        'Notification Sent'
    )
    times_notification_sent = fields.Integer(
        'Times launched',
        readonly=True
    )
    firebase_initialized = fields.Boolean(
        string='Firebase Initialized',
        default=False
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
    ], string='Estado', default='draft', readonly=True, required=True)
    scheduled_datetime = fields.Datetime('Scheduled Time')

    def initialize_firebase(self):
        if not firebase_admin._apps:
            notification_data = self.env['firebase.data'].search([], limit=1)
            if notification_data:
                cred = credentials.Certificate(notification_data.get_credentials())
                firebase_admin.initialize_app(cred)
                self.firebase_initialized = True

    @api.onchange('image_preview')
    def _onchange_image_upload(self):
        if self.image_preview:
            # Generar una URL pública para la imagen
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            image_url = "{}/web/image/firebase.notification/{}/image_preview".format(base_url, self.id)
            # Actualizar el campo 'image' con la URL pública
            self.image = image_url

    @api.onchange('scheduled_datetime')
    def _onchange_scheduled_datetime(self):
        self.notification_sent = False

    def send_scheduled_notifications(self):
        now = fields.Datetime.now()
        scheduled_notifications = self.search([
            ('scheduled_datetime', '<=', now),
            ('notification_sent', '=', False)
        ])
        for notification in scheduled_notifications:
            notification.send_to_topic()

    def send_to_topic(self):
        self.initialize_firebase()
        topic = 'appUserTopic'

        notification = messaging.Notification(
            title=self.title,
            body=self.body
        )

        data = {k: v for k, v in {'image': self.image, 'redirect_url': self.redirect_url}.items() if v}

        android_config = messaging.AndroidConfig(
            notification=messaging.AndroidNotification(image=self.image)
        ) if self.image else None

        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(mutable_content=True)
            ),
            fcm_options=messaging.APNSFCMOptions(image=self.image)
        ) if self.image else None

        webpush_config = messaging.WebpushConfig(
            notification=messaging.WebpushNotification(image=self.image)
        ) if self.image else None

        message = messaging.Message(
            notification=notification,
            data=data or None,
            android=android_config,
            apns=apns_config,
            webpush=webpush_config,
            topic=topic,
        )

        self.last_launch = datetime.now()

        response = messaging.send(message)

        if response:
            self.state = 'sent'

        self.notification_sent = True
        self.times_notification_sent += 1
        print('Successfully sent message:', response)

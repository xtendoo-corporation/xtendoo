# -*- coding: utf-8 -*-

import logging

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class mail_thread(models.AbstractModel):
    """
    Overwrite to redefine message routing and process corresponding exceptions
    """
    _inherit = "mail.thread"

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """
        Overwrite to catch and mark unattached messages

        1. Send notificaion if defined in settings
        """
        res = []
        try:
            res = super(mail_thread, self).message_route(
                message, message_dict, model=model,
                thread_id=thread_id, custom_values=custom_values
            )
        except ValueError:

            print("*"*80)
            print("*message_dict*", message_dict)
            print("*"*80)

            parent_object_id = None
            user_id = self._get_email_to_user(message_dict)

            if user_id and user_id.company_id:
                parent_object_id = self._get_email_from_partner(user_id, message_dict)

            if parent_object_id:
                message_dict.update({
                    "model": "res.partner",
                    "res_id": parent_object_id.id,
                })
            else:
                parent_object_id = self._get_lost_parent()
                message_dict.update({
                    "model": "lost.message.parent",
                    "res_id": parent_object_id.id,
                })

            message_id = self._create_lost_message(**message_dict)
            _logger.warning(u"Message {} can't be routed. Assign it to 'lost messages'".format(message_id))

            if user_id:
                self._create_lost_notification(user_id, parent_object_id)

        return res

    @api.returns("mail.message", lambda value: value.id)
    def _create_lost_message(self, *,
                             body="", subject=None, message_type="notification",
                             email_from=None, author_id=None, parent_id=False,
                             subtype_xmlid=None, subtype_id=False, partner_ids=None,
                             attachments=None, attachment_ids=None,
                             add_sign=True, record_name=False,
                             **kwargs):
        """
        The method to prepare lost message and create it.
        It represents a modified copy of message_post
        """
        msg_kwargs = dict((key, val) for key, val in kwargs.items() if key in self.env["mail.message"]._fields)
        author_id, email_from = self._message_compute_author(author_id, email_from, raise_exception=True)
        if subtype_xmlid:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail_mt_note")

        values = dict(msg_kwargs)
        values.update({
            "is_unattached": True,
            "author_id": author_id,
            "email_from": email_from,
            "body": body,
            "subject": subject or False,
            "message_type": message_type,
            "parent_id": parent_id,
            "subtype_id": subtype_id,
            "partner_ids": set(partner_ids or []),
            "add_sign": add_sign,
            "record_name": record_name,
        })

        attachments = attachments or []
        attachment_ids = attachment_ids or []
        attachement_values = self._message_post_process_attachments(attachments, attachment_ids, values)
        values.update(attachement_values)
        message_id = self._message_create(values)
        return message_id

    def _create_lost_notification(self, user_id, parent_object_id):
        self.env['mail.message'].create({
            'message_type': 'notification',
            'subject': 'Email recibido',
            'model': 'res.partner',
            'res_id': parent_object_id.id,
            'partner_ids': [user_id.id],
            'author_id': self.env.user.partner_id.id,
            'notification_ids': [(0, 0, {
                'res_partner_id': self.env.user.partner_id.id,
                'notification_type': 'inbox',
            })],
        })

    @api.model
    def _get_lost_parent(self):
        """
        The method to find or create a parent object which would server to overcome super rights

        Returns:
         * lost.message.parent object
        """
        self = self.sudo()
        lost_parent_id = self.env["lost.message.parent"].search([], limit=1)
        if not lost_parent_id:
            lost_parent_id = self.env["lost.message.parent"].create({})
        return lost_parent_id

    @api.model
    def _get_email_to_user(self, message_dict):
        email_to = message_dict.get("to")
        if not email_to:
            return None

        email_to = email_to.split('<')[-1].split('>')[0]
        user_id = self.env['res.users'].sudo().search([
            ('email', '=', email_to)], limit=1)
        return user_id

    @api.model
    def _get_email_from_partner(self, user_id, message_dict):
        email_from = message_dict.get("email_from")
        if not email_from:
            return None

        partner_id = self.env['res.partner'].sudo().search([
            ('email', '=', tools.email_normalize(email_from)), ('company_id', '=', user_id.company_id.id)], limit=1)

        if not partner_id:
            partner_id = self.env['res.partner'].sudo().search([
                ('email', '=', tools.email_normalize(email_from))], limit=1)

        return partner_id

# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    whatsapp_session_state = fields.Selection(
        selection=[
            ("idle", "Idle"),
            ("waiting_incident", "Waiting for Incident"),
        ],
        string="WhatsApp Session State",
        default="idle",
    )
    whatsapp_ticket_type_id = fields.Many2one(
        "helpdesk.ticket.type",
        string="Selected WhatsApp Ticket Type",
    )
    last_incident_request_date = fields.Datetime(
        string="Last Incident Request Date",
    )

    def message_post(self, **kwargs):
        """
        Ensure the partner's communication manager is subscribed to the channel.
        Also mirror the WhatsApp messages to the partner's open ticket.
        """
        # Create the message first to capture body, attachments, etc.
        res = super().message_post(**kwargs)

        if self.channel_type == 'whatsapp':
            # Identify partner from phone token
            partner = self.env['res.partner'].search([
                ('phone_sanitized', 'ilike', self.gateway_channel_token)
            ], limit=1)
            
            if partner:
                manager = partner.communication_manager_id or self.env.company.whatsapp_default_manager_id
                if manager and manager.partner_id not in self.channel_partner_ids:
                    self.write({'channel_partner_ids': [(4, manager.partner_id.id)]})

                # Check for open ticket
                open_ticket = self.env["helpdesk.ticket"].sudo().search([
                    ("partner_id", "=", partner.id),
                    ("stage_id.closed", "=", False)
                ], limit=1)

                # Avoid recursive loops when posting to the ticket
                if open_ticket and not self._context.get('whatsapp_no_mirror'):
                    body = res.body
                    if not body and res.attachment_ids:
                        body = "<i>Archivo adjunto enviado por WhatsApp</i>"
                    
                    if body:
                        # Prefix to identify it came from WhatsApp
                        prefix = "<b>Mensaje de WhatsApp:</b><br/>"
                        
                        # Copy attachments so they aren't stolen from the channel
                        copied_attachment_ids = []
                        for att in res.attachment_ids.sudo():
                            new_att = att.copy({
                                'res_model': 'helpdesk.ticket',
                                'res_id': open_ticket.id,
                            })
                            copied_attachment_ids.append(new_att.id)

                        # Post on the ticket
                        open_ticket.with_context(whatsapp_no_mirror=True).message_post(
                            body=prefix + body,
                            author_id=res.author_id.id if res.author_id else self.env.user.partner_id.id,
                            message_type=res.message_type,
                            subtype_xmlid="mail.mt_comment",
                            attachment_ids=copied_attachment_ids,
                        )

        return res

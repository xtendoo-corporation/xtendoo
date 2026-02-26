# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


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

        _logger.info("WhatsApp Automation (Mirror): message_post intercepted for channel %s. channel_type is: '%s'", self.id, self.channel_type)

        # Check if this is a WhatsApp channel
        if self.channel_type == 'whatsapp':
            _logger.info("WhatsApp Automation (Mirror): Intercepting message_post in WhatsApp channel %s", self.id)
            
            # Identify if any partner in this channel has an open ticket
            open_ticket = self.env["helpdesk.ticket"].sudo().search([
                ("partner_id", "in", self.channel_partner_ids.ids),
                ("stage_id.closed", "=", False)
            ], limit=1)

            if open_ticket:
                _logger.info("WhatsApp Automation (Mirror): Found open ticket #%s for partners %s", open_ticket.number, self.channel_partner_ids.ids)
                
                if not self._context.get('whatsapp_no_mirror'):
                    body = res.body
                    _logger.info("WhatsApp Automation (Mirror): Original body: '%s', Attachments: %s", body, len(res.attachment_ids))
                    
                    if not body and res.attachment_ids:
                        body = "<i>Archivo adjunto enviado por WhatsApp</i>"
                    
                    if body:
                        # Determine author name
                        author_name = res.author_id.name if res.author_id else "Bot"
                        prefix = f"<b>Mensaje de WhatsApp ({author_name}):</b><br/>"
                        
                        # Copy attachments
                        copied_attachment_ids = []
                        for att in res.attachment_ids.sudo():
                            new_att = att.copy({
                                'res_model': 'helpdesk.ticket',
                                'res_id': open_ticket.id,
                            })
                            copied_attachment_ids.append(new_att.id)

                        _logger.info("WhatsApp Automation (Mirror): Preparing to mirror message to ticket.")

                        # Post on the ticket
                        try:
                            open_ticket.with_context(whatsapp_no_mirror=True).message_post(
                                body=prefix + body,
                                author_id=res.author_id.id if res.author_id else self.env.user.partner_id.id,
                                message_type=res.message_type,
                                subtype_xmlid="mail.mt_comment",
                                attachment_ids=copied_attachment_ids,
                            )
                            _logger.info("WhatsApp Automation (Mirror): Successfully mirrored message to ticket #%s.", open_ticket.number)
                        except Exception as e:
                            _logger.error("WhatsApp Automation (Mirror): Failed to mirror message to ticket. Error: %s", e)
                    else:
                        _logger.info("WhatsApp Automation (Mirror): Ignored message (no body and no attachments).")
                else:
                    _logger.info("WhatsApp Automation (Mirror): Ignored message due to 'whatsapp_no_mirror' context.")
            else:
                _logger.info("WhatsApp Automation (Mirror): No open ticket found for partners %s in this channel.", self.channel_partner_ids.ids)
                    
            # Try to add the communication manager to the channel (original logic)
            partner = self.env['res.partner'].search([
                ('phone_sanitized', 'ilike', self.gateway_channel_token)
            ], limit=1) if hasattr(self, 'gateway_channel_token') and self.gateway_channel_token else False
            
            if not partner:
                # Fallback: find the non-internal user in the channel
                for p in self.channel_partner_ids:
                    if not p.user_ids or not p.user_ids[0].has_group('base.group_user'):
                        partner = p
                        break
            
            if partner:
                manager = partner.communication_manager_id or self.env.company.whatsapp_default_manager_id
                if manager and manager.partner_id not in self.channel_partner_ids:
                    self.write({'channel_partner_ids': [(4, manager.partner_id.id)]})

        return res

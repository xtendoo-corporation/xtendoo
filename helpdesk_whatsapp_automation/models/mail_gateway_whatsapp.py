# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MailGatewayWhatsapp(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _process_update(self, chat, message, value):
        """
        Override _process_update to handle the /ticket command and incident reports.
        """
        # Call super to ensure normal message processing (chatter integration, etc.)
        super()._process_update(chat, message, value)

        partner = self._get_author(chat.gateway_id, value)
        if not partner or partner._name != "res.partner":
            return

        # Ensure communication manager receives a copy: add them to the channel
        manager = partner.communication_manager_id or self.env.company.whatsapp_default_manager_id
        if manager and manager.partner_id not in chat.channel_partner_ids:
            chat.write({"channel_partner_ids": [(4, manager.partner_id.id)]})

        # Capture button response (interactive message)
        interactive = message.get("interactive", {})
        button_text = ""
        if interactive.get("type") == "button_reply":
            button_text = interactive.get("button_reply", {}).get("title", "").strip()
            _logger.info("WhatsApp Automation: Received button reply: %s", button_text)

        body = message.get("text", {}).get("body", "").strip() if message.get("text") else ""
        
        # Use button text as body if it's a button reply
        input_text = button_text or body
        if not input_text:
            return

        # Handle /ticket command
        if input_text.lower() == "/ticket":
            self._handle_ticket_command(chat, partner)
            return

        # Check if the input_text matches a ticket type (Duda, Solicitud nuevo cambio, Error)
        ticket_type = self.env["helpdesk.ticket.type"].sudo().search([
            ("name", "=ilike", input_text)
        ], limit=1)

        if ticket_type and chat.whatsapp_session_state == "idle":
             chat.write({"whatsapp_ticket_type_id": ticket_type.id})
             _logger.info("WhatsApp Automation: Selected Ticket Type: %s", ticket_type.name)
             # Optional: If you want to automatically trigger /ticket after selection
             # self._handle_ticket_command(chat, partner)
             return

        # Handle incident description if waiting for it
        if chat.whatsapp_session_state == "waiting_incident":
            self._handle_incident_report(chat, partner, input_text)

    def _handle_ticket_command(self, chat, partner):
        """
        Start the ticket creation flow by asking for the incident description.
        """
        _logger.info("Handling /ticket command for partner %s", partner.name)
        
        chat.write({
            "whatsapp_session_state": "waiting_incident",
            "last_incident_request_date": fields.Datetime.now(),
        })

        # Send incident request template from configuration
        template = self.env.company.incident_request_template_id
        
        if template:
            # Code to send template via gateway
            notification = self.env['mail.notification'].sudo().create({
                'mail_message_id': chat.message_post(
                    body=template.body,
                    subtype_xmlid="mail.mt_comment",
                ).id,
                'res_partner_id': partner.id,
            })
            notification.gateway_channel_id = chat
            
            self.with_context(whatsapp_template_id=template.id)._send(
                gateway=chat.gateway_id,
                record=notification
            )
        else:
            # Fallback if no template is configured
            chat.message_post(
                body=_("Please describe the incident you would like to report. (No WhatsApp template configured in settings)"),
                subtype_xmlid="mail.mt_comment",
            )

    def _handle_incident_report(self, chat, partner, body):
        """
        Create a helpdesk ticket from the incident description and notify the employee.
        """
        _logger.info("Creating ticket for partner %s: %s", partner.name, body[:50])

        # Create the ticket
        ticket_vals = {
            "name": _("WhatsApp Incident: %s") % body[:50],
            "description": body,
            "partner_id": partner.id,
            "type_id": chat.whatsapp_ticket_type_id.id or False,
            "user_id": partner.communication_manager_id.id or False,
            "channel_id": self.env.ref("helpdesk_mgmt.helpdesk_ticket_channel_whatsapp", raise_if_not_found=False).id or self.env.ref("helpdesk_mgmt.helpdesk_ticket_channel_other").id,
        }
        
        ticket = self.env["helpdesk.ticket"].sudo().create(ticket_vals)

        # Reset session state
        chat.write({
            "whatsapp_session_state": "idle",
            "whatsapp_ticket_type_id": False,
        })

        # Mention the communication employee in the chatter
        if partner.communication_employee_id:
            mention_body = _("<p>New ticket created from WhatsApp: <a href='/web#id=%s&model=helpdesk.ticket&view_type=form'>%s</a></p>"
                             "<p>Employee to notify: <a href='/web#id=%s&model=res.partner&view_type=form'>@%s</a></p>") % (
                ticket.id, ticket.number, partner.communication_employee_id.partner_id.id, partner.communication_employee_id.name
            )
            chat.message_post(
                body=mention_body,
                subtype_xmlid="mail.mt_comment",
                partner_ids=[partner.communication_employee_id.partner_id.id]
            )
            
            # Also post to the ticket's chatter
            ticket.message_post(
                body=_("Ticket created from WhatsApp conversation. Assigned manager: %s") % partner.communication_manager_id.name,
                subtype_xmlid="mail.mt_note",
            )

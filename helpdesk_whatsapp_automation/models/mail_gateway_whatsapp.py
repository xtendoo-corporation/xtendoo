# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MailGatewayWhatsapp(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _get_author(self, gateway, update):
        """
        Override to ensure we always return a singleton.
        If a phone number is registered to multiple partners, the base module
        might return a recordset of multiple partners, causing an 'Expected singleton'
        error when it tries to read author.id.
        """
        author = super()._get_author(gateway, update)
        if author and len(author) > 1:
            _logger.warning("WhatsApp Automation: Multiple authors found for %s. Using the first one.", author)
            return author[0]
        return author

    def _process_update(self, chat, message, value):
        """
        Override _process_update to handle the /ticket command and incident reports.
        """
        # Call super to ensure normal message processing (chatter integration, etc.)
        super()._process_update(chat, message, value)

        _logger.info("WhatsApp Automation: Processing update for channel %s", chat.name)
        _logger.info("WhatsApp Automation: Raw message: %s", message)
        
        # Grab the message that was just created in the channel by the base module
        last_mail_message = self.env['mail.message'].sudo().search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', chat.id),
        ], order='id desc', limit=1)
        
        partner = self._get_author(chat.gateway_id, value)
        if not partner or partner._name != "res.partner":
            _logger.info("WhatsApp Automation: Message ignored (author is not a partner or not found)")
            return

        # Ensure communication manager receives a copy: add them to the channel
        manager = partner.communication_manager_id or self.env.company.whatsapp_default_manager_id
        if manager and manager.partner_id not in chat.channel_partner_ids:
            _logger.info("WhatsApp Automation: Adding manager %s to channel followers", manager.name)
            chat.write({"channel_partner_ids": [(4, manager.partner_id.id)]})

        # Check if the partner already has an open ticket (not closed).
        # If they do, we bypass the automation so they can talk naturally to the agent.
        open_ticket = self.env["helpdesk.ticket"].sudo().search([
            ("partner_id", "=", partner.id),
            ("stage_id.closed", "=", False)
        ], limit=1)

        if open_ticket:
            _logger.info("WhatsApp Automation: Partner has open ticket #%s. Bypassing automation menu.", open_ticket.number)
            # Make sure session state is idle so it doesn't get stuck waiting for an incident
            if chat.whatsapp_session_state != "idle":
                chat.write({
                    "whatsapp_session_state": "idle",
                    "whatsapp_ticket_type_id": False,
                })
            return

        # Capture button response (interactive message)
        interactive = message.get("interactive", {})
        button_reply = message.get("button", {}) # For some button types
        button_text = ""
        
        if interactive.get("type") == "button_reply":
            button_text = interactive.get("button_reply", {}).get("title", "").strip()
        elif button_reply:
            button_text = button_reply.get("text", "").strip()
        
        if button_text:
            _logger.info("WhatsApp Automation: Received button reply: %s", button_text)

        body = message.get("text", {}).get("body", "").strip() if message.get("text") else ""
        
        # Try to get caption from media if body is empty
        if not body:
            for media_type in ["image", "document", "video", "audio", "sticker"]:
                if message.get(media_type) and message.get(media_type).get("caption"):
                    body = message.get(media_type).get("caption").strip()
                    _logger.info("WhatsApp Automation: extracted caption from %s", media_type)
                    break

        # Use button text as body if it's a button reply
        input_text = button_text or body
        
        # If we still have no text, check for specific 'button' field (Template Quick Replies)
        if not input_text and message.get("type") == "button":
            input_text = message.get("button", {}).get("text", "").strip()
            _logger.info("WhatsApp Automation: Received template button: %s", input_text)

        # Handle purely attachment messages or mixed messages
        if chat.whatsapp_session_state == "waiting_incident":
            if not input_text and last_mail_message.attachment_ids:
                # User sent an image/PDF without any text caption
                input_text = _("Incidencia reportada mediante archivo adjunto")
            elif input_text and last_mail_message.attachment_ids:
                # User sent text AND an attachment (captioned image) - keep the text
                _logger.info("WhatsApp Automation: Received text with attachments: %s", input_text)
            elif not input_text:
                _logger.info("WhatsApp Automation: No text content or attachments found in message (Type: %s)", message.get("type"))
                return
        elif not input_text:
            _logger.info("WhatsApp Automation: No text content found in message (Type: %s)", message.get("type"))
            return

        _logger.info("WhatsApp Automation: Input detected: '%s' (State: %s)", input_text, chat.whatsapp_session_state)

        # Check if the input_text matches a ticket type (Duda, Solicitud nuevo cambio, Error)
        ticket_type = self.env["helpdesk.ticket.type"].sudo().search([
            ("name", "=ilike", input_text)
        ], limit=1)

        if ticket_type:
            _logger.info("WhatsApp Automation: Ticket type '%s' selected", ticket_type.name)
            # If they select a type (via button or text), we set it and ask for details
            chat.write({
                "whatsapp_ticket_type_id": ticket_type.id,
                "whatsapp_session_state": "waiting_incident",
                "last_incident_request_date": fields.Datetime.now(),
            })
            _logger.info("WhatsApp Automation: Selected Ticket Type: %s", ticket_type.name)
            
            # Send specific prompt based on type
            prompts = {
                "Error": _(
                    "Gracias 👍\n\n"
                    "Para revisar la incidencia necesitamos que nos indiques:\n"
                    "• Qué acción estabas realizando\n"
                    "• Qué mensaje de error aparece (texto exacto)\n"
                    "• En qué momento ocurre\n\n"
                    "Si puedes adjuntar captura de pantalla, mejor aún."
                ),
                "Consulta": _(
                    "Perfecto 👍\n\n"
                    "Para poder resolver tu consulta, indícanos por favor:\n"
                    "• En qué módulo o sección estás trabajando\n"
                    "• Qué quieres conseguir exactamente\n"
                    "• Qué es lo que no tienes claro\n\n"
                    "Con esa información podremos ayudarte más rápido."
                ),
                "Llamame": _(
                    "Perfecto 👍\n\n"
                    "Hemos registrado tu solicitud de llamada.\n"
                    "Por favor, indícanos brevemente:\n"
                    "• El motivo de la llamada\n"
                    "• Tu disponibilidad horaria preferida\n\n"
                    "Un empleado se pondrá en contacto contigo lo antes posible."
                ),
            }
            
            # Find closest match in prompts keys
            prompt_key = next((k for k in prompts if k.lower() in ticket_type.name.lower()), False)
            message_body = prompts.get(prompt_key, _("Porfavor introduce información al respecto a continuación sobre el motivo (Cuanta más información mejor, gracias)."))
            
            _logger.info("WhatsApp Automation: Sending prompt for %s", ticket_type.name)
            self._send_whatsapp_text(chat, partner, message_body)
            return

        # Handle incident description if waiting for it
        if chat.whatsapp_session_state == "waiting_incident":
            self._handle_incident_report(chat, partner, input_text, last_mail_message)
            return

        # Catch-all: If not waiting for an incident and no ticket type selected,
        # treat ANY message as a request to start a new ticket flow.
        _logger.info("WhatsApp Automation: Any text recognized as trigger for new ticket menu")
        self._handle_ticket_command(chat, partner)

    def _send_whatsapp_text(self, chat, partner, body):
        """
        Send a free-text message through the WhatsApp gateway.
        """
        notification = self.env['mail.notification'].sudo().create({
            'mail_message_id': chat.message_post(
                body=body,
                subtype_xmlid="mail.mt_comment",
            ).id,
            'res_partner_id': partner.id,
        })
        notification.gateway_channel_id = chat
        
        # Trigger the gateway send logic
        self._send(
            gateway=chat.gateway_id,
            record=notification
        )

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
            self._send_whatsapp_text(
                chat, partner, 
                _("Please describe the incident you would like to report. (No WhatsApp template configured in settings)")
            )

    def _handle_incident_report(self, chat, partner, body, original_message=None):
        """
        Create a helpdesk ticket from the incident description and notify the employee.
        """
        _logger.info("WhatsApp Automation: Creating ticket for partner %s with type %s", 
                     partner.name, chat.whatsapp_ticket_type_id.name or "None")

        # Safely get the channel ID or create "WhatsApp" channel if missing
        whatsapp_channel = self.env.ref("helpdesk_mgmt.helpdesk_ticket_channel_whatsapp", raise_if_not_found=False)
        if not whatsapp_channel:
            whatsapp_channel = self.env["helpdesk.ticket.channel"].sudo().search([("name", "=ilike", "WhatsApp")], limit=1)
            if not whatsapp_channel:
                whatsapp_channel = self.env["helpdesk.ticket.channel"].sudo().create({"name": "WhatsApp"})
        
        channel_id = whatsapp_channel.id

        # Create the ticket
        ticket_vals = {
            "name": _("WhatsApp Incident: %s") % body[:50],
            "description": body,
            "partner_id": partner.id,
            "type_id": chat.whatsapp_ticket_type_id.id or False,
            "user_id": partner.communication_manager_id.id or False,
            "assigned_employee_id": partner.communication_employee_id.id or False,
            "channel_id": channel_id,
        }
        
        ticket = self.env["helpdesk.ticket"].sudo().create(ticket_vals)
        _logger.info("WhatsApp Automation: Ticket created successfully: #%s", ticket.number)

        # Copy original message attachments to the ticket
        if original_message and original_message.sudo().attachment_ids:
            _logger.info("WhatsApp Automation: Attaching %d files to ticket %s", len(original_message.attachment_ids), ticket.number)
            for attachment in original_message.sudo().attachment_ids:
                attachment.copy({
                    'res_model': 'helpdesk.ticket',
                    'res_id': ticket.id,
                })

        # Confirm to the user
        self._send_whatsapp_text(
            chat, partner,
            _("✅ Gracias. Tu incidencia ha sido registrada con el número #%s. Un agente la revisará y se pondrá en contacto contigo lo antes posible.") % ticket.number
        )

        # Notify assigned employee/manager via email
        if ticket.assigned_employee_id or ticket.user_id:
            template = self.env.ref("helpdesk_whatsapp_automation.email_template_assigned_employee_whatsapp_ticket_v2", raise_if_not_found=False)
            if template:
                email_to_list = []
                if ticket.assigned_employee_id and ticket.assigned_employee_id.email_formatted:
                    email_to_list.append(ticket.assigned_employee_id.email_formatted.replace('\n', '').replace('\r', ''))
                if ticket.user_id and ticket.user_id.email_formatted:
                    email_to_list.append(ticket.user_id.email_formatted.replace('\n', '').replace('\r', ''))
                
                email_from = ticket.company_id.email_formatted or self.env.user.email_formatted
                if email_from:
                    email_from = email_from.replace('\n', '').replace('\r', '')

                if email_to_list:
                    email_values = {
                        'email_to': ','.join(email_to_list),
                        'email_from': email_from,
                    }
                    _logger.info("WhatsApp Automation: Sending assignment email for ticket #%s to %s.", ticket.number, email_values['email_to'])
                    template.sudo().send_mail(ticket.id, force_send=True, email_values=email_values)
                else:
                    _logger.warning("WhatsApp Automation: No valid email addresses found for ticket #%s assignment.", ticket.number)
            else:
                _logger.warning("WhatsApp Automation: Assignment email template not found.")

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

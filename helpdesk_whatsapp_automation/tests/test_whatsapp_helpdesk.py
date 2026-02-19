# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common
from odoo import fields


class TestWhatsappHelpdesk(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Client",
            "mobile": "+34600000000",
        })
        cls.manager = cls.env["res.users"].create({
            "name": "Communication Manager",
            "login": "comm_manager",
            "email": "manager@test.com",
            "groups_id": [(4, cls.env.ref("base.group_user").id)],
        })
        cls.partner.communication_manager_id = cls.manager

        cls.gateway = cls.env["mail.gateway"].create({
            "name": "Test WhatsApp Gateway",
            "gateway_type": "whatsapp",
        })
        
        cls.channel = cls.env["discuss.channel"].create({
            "name": "WhatsApp Channel",
            "channel_type": "whatsapp",
            "gateway_id": cls.gateway.id,
            "gateway_channel_token": "346600000000", # Fixed token for searchRead if needed
        })
        # Important: channel_type is set but gateway_channel_token should match search in discuss_channel.py
        cls.channel.gateway_channel_token = "34600000000"

        # Create dummy template and set in company
        cls.template = cls.env["mail.whatsapp.template"].create({
            "name": "Test Incident Template",
            "body": "Describe your incident",
            "category": "utility",
            "language": "en",
            "gateway_id": cls.gateway.id,
        })
        cls.env.company.incident_request_template_id = cls.template

    def test_whatsapp_ticket_flow(self):
        """Test the full flow from /ticket to ticket creation"""
        MailGatewayWhatsapp = self.env["mail.gateway.whatsapp"]

        # 1. Simulate receiving /ticket
        message_ticket = {
            "type": "text",
            "text": {"body": "/ticket"},
            "from": "34600000000",
            "timestamp": "1620000000",
        }
        value = {"contacts": [{"wa_id": "34600000000", "profile": {"name": "Test Client"}}]}
        
        MailGatewayWhatsapp._process_update(self.channel, message_ticket, value)

        # Check state changed to waiting_incident
        self.assertEqual(self.channel.whatsapp_session_state, "waiting_incident")
        
        # Check manager was added as follower
        self.assertIn(self.manager.partner_id, self.channel.channel_partner_ids)

        # 2. Simulate receiving incident description
        incident_description = "I have a problem with my router."
        message_incident = {
            "type": "text",
            "text": {"body": incident_description},
            "from": "34600000000",
            "timestamp": "1620000060",
        }

        MailGatewayWhatsapp._process_update(self.channel, message_incident, value)

        # Check ticket was created
        ticket = self.env["helpdesk.ticket"].search([("partner_id", "=", self.partner.id)], order="id desc", limit=1)
        self.assertTrue(ticket)
        self.assertEqual(ticket.user_id, self.manager)

    def test_default_manager_fallback(self):
        """Test fallback to company default manager"""
        # Set company default manager
        self.env.company.whatsapp_default_manager_id = self.manager
        
        # Create partner without manager
        partner_no_manager = self.env["res.partner"].create({
            "name": "No Manager Partner",
            "mobile": "+34611111111",
        })
        
        # Check it uses company default
        self.assertEqual(partner_no_manager.communication_manager_id, self.manager)
        
        # Create new channel for this partner
        channel = self.env["discuss.channel"].create({
            "name": "New Channel",
            "channel_type": "whatsapp",
            "gateway_channel_token": "34611111111",
        })
        
        # Simulate message
        channel.message_post(body="Hello", message_type="comment")
        
        # Check manager was auto-added to channel
        self.assertIn(self.manager.partner_id, channel.channel_partner_ids)

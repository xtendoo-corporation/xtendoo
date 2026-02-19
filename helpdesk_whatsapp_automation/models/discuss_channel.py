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
        """
        if self.channel_type == 'whatsapp':
            partner = self.env['res.partner'].search([
                ('phone_sanitized', 'ilike', self.gateway_channel_token)
            ], limit=1)
            
            if partner:
                manager = partner.communication_manager_id or self.env.company.whatsapp_default_manager_id
                if manager and manager.partner_id not in self.channel_partner_ids:
                    self.write({'channel_partner_ids': [(4, manager.partner_id.id)]})
                    
        return super().message_post(**kwargs)

# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_default_manager_id = fields.Many2one(
        related="company_id.whatsapp_default_manager_id",
        readonly=False,
    )
    incident_request_template_id = fields.Many2one(
        related="company_id.incident_request_template_id",
        readonly=False,
    )

    def set_values(self):
        """
        Propagate the default communication manager to existing partners
        that don't have one assigned yet.
        """
        import logging
        _logger = logging.getLogger(__name__)

        super().set_values()
        
        # We use the company from the configuration record
        company = self.company_id
        manager = self.whatsapp_default_manager_id
        
        _logger.info("WhatsApp Automation DEBUG: Company: %s, Manager: %s", company.name, manager.name if manager else "None")

        if manager:
            # We search for ALL partners that don't have a manager set
            partners = self.env["res.partner"].sudo().search([
                ("communication_manager_id", "=", False)
            ])
            _logger.info("WhatsApp Automation DEBUG: Found %s partners without manager", len(partners))
            
            if partners:
                # Update them
                partners.write({"communication_manager_id": manager.id})
                _logger.info("WhatsApp Automation DEBUG: Propagation finished successfully")
            else:
                _logger.info("WhatsApp Automation DEBUG: All partners already have a manager")
        else:
            _logger.info("WhatsApp Automation DEBUG: No manager selected, skipping propagation")

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
        
        # We need to make sure the value is persisted in company before reading
        self.env.cr.execute("SELECT whatsapp_default_manager_id FROM res_company WHERE id = %s", [self.company_id.id])
        res = self.env.cr.fetchone()
        manager_id = res[0] if res else False
        
        _logger.info("WhatsApp Automation DEBUG: Persisted Manager ID in Company: %s", manager_id)

        if manager_id:
            # First, check how many partners have NO manager
            self.env.cr.execute("SELECT count(*) FROM res_partner WHERE communication_manager_id IS NULL OR communication_manager_id = 0")
            count_empty = self.env.cr.fetchone()[0]
            _logger.info("WhatsApp Automation DEBUG: Total partners with EMPTY manager BEFORE update: %s", count_empty)

            if count_empty > 0:
                # Update them
                self.env.cr.execute("UPDATE res_partner SET communication_manager_id = %s WHERE communication_manager_id IS NULL OR communication_manager_id = 0", [manager_id])
                self.env.cr.commit() # Force commit to ensure visibility
                _logger.info("WhatsApp Automation DEBUG: SQL affected %s rows", self.env.cr.rowcount)
            
            # Final check
            self.env.cr.execute("SELECT count(*) FROM res_partner WHERE communication_manager_id = %s", [manager_id])
            count_filled = self.env.cr.fetchone()[0]
            _logger.info("WhatsApp Automation DEBUG: Total partners WITH manager %s AFTER update: %s", manager_id, count_filled)
            
            self.env['res.partner'].sudo().invalidate_model(['communication_manager_id'])
        else:
            _logger.warning("WhatsApp Automation DEBUG: No manager ID found to propagate")

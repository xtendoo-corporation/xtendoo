# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class mail_message(models.Model):
    """
    Overwrite to introduce re-routing methods
    """
    _inherit = "mail.message"

    is_unattached = fields.Boolean(string="Unattached message")

    def action_attach(self):
        """
        Method to return 'attach message wizard'

        Returns:
         * aciton dict
        """
        return {
            'name': _("Route Message"),
            'res_model': 'mail.message.attach.wizard',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_message_ids': [(6, 0, self.ids)],
            },
        }

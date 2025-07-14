from odoo import api, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    @api.model
    def default_get(self, fields_list):
        """Override default_get to set l10n_es_edi_facturae_checkbox_xml based on partner settings"""
        res = super().default_get(fields_list)

        if 'l10n_es_edi_facturae_checkbox_xml' in fields_list and 'move_ids' in res:
            move_ids = self.env['account.move'].browse(res.get('move_ids', []))
            if move_ids:
                # Get all unique partners from the invoices
                partners = move_ids.mapped('partner_id')
                # Only enable facturae if ALL partners have it enabled
                res['l10n_es_edi_facturae_checkbox_xml'] = all(partner.facturae for partner in partners) if partners else False

        return res

    @api.depends('move_ids')
    def _compute_l10n_es_edi_facturae_checkbox_xml(self):
        """Compute facturae checkbox based on partner settings"""
        for wizard in self:
            if hasattr(wizard, 'l10n_es_edi_facturae_enable_xml') and wizard.l10n_es_edi_facturae_enable_xml:
                # Check if all partners have facturae enabled
                partners = wizard.move_ids.mapped('partner_id')
                wizard.l10n_es_edi_facturae_checkbox_xml = all(partner.facturae for partner in partners) if partners else False
            else:
                wizard.l10n_es_edi_facturae_checkbox_xml = False

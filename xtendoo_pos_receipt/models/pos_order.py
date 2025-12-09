from odoo import models
import logging
_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def export_for_ui(self):
        _logger.info("[POS DEBUG] Ejecutando export_for_ui en custom todopintura_pos_receipt")
        data = super().export_for_ui()
        if not data.get('company') or not data['company'].get('name'):
            company = self.env.company
            data['company'] = {
                'name': company.name or '',
                'vat': company.vat or '',
                'street': company.street or '',
                'zip': company.zip or '',
                'city': company.city or '',
                'state_id': {'name': company.state_id.name if company.state_id else ''},
            }
        return data

    def to_json(self):
        _logger.info("[POS DEBUG] Ejecutando to_json en custom todopintura_pos_receipt")
        data = super().to_json()
        if not data.get('company') or not data['company'].get('name'):
            company = self.env.company
            data['company'] = {
                'name': company.name or '',
                'vat': company.vat or '',
                'street': company.street or '',
                'zip': company.zip or '',
                'city': company.city or '',
                'state_id': {'name': company.state_id.name if company.state_id else ''},
            }
        return data

    def export_as_JSON(self):
        _logger.info("[POS DEBUG] Ejecutando export_as_JSON en custom todopintura_pos_receipt")
        data = super().export_as_JSON()
        if not data.get('company') or not data['company'].get('name'):
            company = self.env.company
            data['company'] = {
                'name': company.name or '',
                'vat': company.vat or '',
                'street': company.street or '',
                'zip': company.zip or '',
                'city': company.city or '',
                'state_id': {'name': company.state_id.name if company.state_id else ''},
            }
        return data

    def export_as_json(self):
        _logger.info("[POS DEBUG] Ejecutando export_as_json en custom todopintura_pos_receipt")
        data = super().export_as_json()
        if not data.get('company') or not data['company'].get('name'):
            company = self.env.company
            data['company'] = {
                'name': company.name or '',
                'vat': company.vat or '',
                'street': company.street or '',
                'zip': company.zip or '',
                'city': company.city or '',
                'state_id': {'name': company.state_id.name if company.state_id else ''},
            }
        return data

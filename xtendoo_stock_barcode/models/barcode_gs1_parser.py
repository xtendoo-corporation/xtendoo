# -*- coding: utf-8 -*-

from odoo import models

class BarcodeGs1Parser(models.AbstractModel):
    _name = 'barcode.gs1.parser'
    _description = 'GS1 Barcode Parser'

    def parse_gs1_barcode(self, barcode):
        nomenclature = self.env.company.nomenclature_id
        if not nomenclature or not nomenclature.is_gs1_nomenclature:
            return False

        parsed_data = nomenclature.parse_barcode(barcode)
        if not parsed_data:
            return False

        result = {}
        # Parse standard nomenclature return into a structured dict
        for data in parsed_data:
            data_type = data.get('type')
            value = data.get('value')
            if data_type in ('product', 'product_qty', 'lot', 'package', 'location', 'location_dest'):
                result[data_type] = value
                
        # Handle GS1 specific 'measure' if there is an unknown type but we know GS1 patterns:
        for data in parsed_data:
            rule = data.get('rule')
            if rule and rule.type == 'quantity':
                result['product_qty'] = data.get('value')
            if rule and rule.type == 'lot':
                result['lot'] = data.get('value')

        if not result:
            return False
            
        return result

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_order_lines_for_receipt(self):
        """Sobrescribir para agregar qty_int a las líneas del recibo"""
        lines_data = super()._get_order_lines_for_receipt()

        for line_data in lines_data:
            # Agregar qty_int basado en qty original (antes del formateo)
            if hasattr(self, 'lines'):
                for line in self.lines:
                    if line.full_product_name == line_data.get('productName'):
                        line_data['qty_int'] = int(line.qty)
                        break

        return lines_data

    def _prepare_receipt_line(self, line):
        """Sobrescribir para incluir qty_int"""
        result = super()._prepare_receipt_line(line)
        result['qty_int'] = int(line.qty)
        return result

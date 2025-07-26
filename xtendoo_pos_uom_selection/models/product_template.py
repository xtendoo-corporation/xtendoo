# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_pos_data_fields(self):
        """Añade campos adicionales para el POS relacionados con UoM"""
        fields = super()._get_pos_data_fields()
        fields.extend(['uom_id', 'uom_po_id'])
        return fields


class UomUom(models.Model):
    _inherit = "uom.uom"

    def _get_pos_data_fields(self):
        """Define los campos de UoM que se envían al POS"""
        return [
            'id',
            'name',
            'category_id',
            'factor',
            'factor_inv',
            'uom_type',
            'rounding',
        ]

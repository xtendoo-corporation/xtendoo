# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    custom_line_name = fields.Char(
        string="Nombre personalizado",
        help="Nombre personalizado asignado a esta línea desde el POS.",
    )
    custom_line_price = fields.Float(
        string="Precio personalizado",
        digits="Product Price",
        help="Precio personalizado asignado a esta línea desde el POS.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        """Añadir los campos personalizados a los datos cargados en el POS."""
        fields = super()._load_pos_data_fields(config)
        fields.extend(['custom_line_name', 'custom_line_price'])
        return fields


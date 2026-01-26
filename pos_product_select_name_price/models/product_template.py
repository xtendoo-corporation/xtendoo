# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pos_require_custom_info = fields.Boolean(
        string="POS: Pedir nombre y precio",
        default=False,
        help="Si está activo, al vender este producto en el POS se pedirá "
             "un nombre y precio personalizado para esa línea.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Añadir el campo pos_require_custom_info a los datos cargados en el POS."""
        fields = super()._load_pos_data_fields(config_id)
        fields.append('pos_require_custom_info')
        return fields


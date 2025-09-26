# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductPricelistItem(models.Model):
    _inherit = "product.template"

    @api.onchange("item_ids")
    def check_pricelist(self):
        contador = 0
        for item_id in self.item_ids:
            contador = 0
            for item in self.item_ids:
                if item_id.pricelist_id == item.pricelist_id:
                    contador = contador + 1
        if contador > 1:

            raise ValidationError(
                "No puede asociar la tarifa varias veces a un mismo producto"
            )

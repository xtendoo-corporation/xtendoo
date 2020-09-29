from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('price_unit')
    def _onchage_price_unit(self):
        # Comprar el precio con el de la tarifa
        # if precio es menor q coste:
        #    error por pantalla precio pequeño

        if self.price_unit < self.product_id.standard_price:
            raise UserError(
                _('The unit price can\'t be lower than cost price %.2f') %
                (self.product_id.standard_price)
            )

        raise UserError(
            self.order_id.pricelist_id.name
        )

        # if precio_nuevo != precio_tarifa:
        #    if queire cambiar el precio en la tarifa:
        #       cambiar o crear precio en la tarifa
        #    else
        #       return
